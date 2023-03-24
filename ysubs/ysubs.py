import asyncio
from inspect import isawaitable
from typing import (Any, Awaitable, Callable, Dict, Iterable, List, Optional,
                    TypeVar, Union)

from a_sync import ASyncGenericBase
from eth_typing import ChecksumAddress

from ysubs.exceptions import (NoActiveSubscriptions, SignatureError,
                              SignatureNotAuthorized, SignatureNotProvided)
from ysubs.plan import Plan
from ysubs.subscriber import Subscriber
from ysubs.utils import signatures

T = TypeVar('T')

HeadersEscapeHatch = Union[
    Callable[[dict], bool],
    Callable[[dict], Awaitable[bool]]
]


class ySubs(ASyncGenericBase):
    def __init__(
        self,
        addresses: Iterable[ChecksumAddress],
        url: str,
        asynchronous: bool = False,
        _headers_escape_hatch: Optional[HeadersEscapeHatch] = None,
    ) -> None:
        """
        addresses: an iterable of addresses for Subscriber contracts that you have deployed for your program
        url: your website for your service
        """
        
        if not isinstance(url, str):
            raise TypeError(f"'url' must be a string. You passed {url}")
        self.url = url
        
        if not isinstance(asynchronous, bool):
            raise TypeError(f"'asynchronous' must be boolean. You passed {asynchronous}")
        self.asynchronous = asynchronous
        
        if _headers_escape_hatch is not None and not callable(_headers_escape_hatch):
            msg = "_headers_escape_hatch must a callable that accepts a dict and returns either:\n\n"
            msg += " - a boolean value\n"
            msg += " - an awaitable that returns a boolean when awaited.\n\n"
            msg += f"You passed {_headers_escape_hatch}"
            raise TypeError(msg)
        self._headers_escape_hatch = _headers_escape_hatch
        
        self.subscribers = [Subscriber(address, asynchronous=asynchronous) for address in addresses]
    
    ##########
    # System #
    ##########
    
    async def get_all_plans(self) -> Dict[Subscriber, List[Plan]]:
        """
        Returns all Plans defined on each Subscriber.
        """
        plans = await asyncio.gather(*[subscriber.get_all_plans(sync=False) for subscriber in self.subscribers])
        return dict(zip(self.subscribers, plans))
    
    #################
    # Informational #
    #################
    
    async def get_active_subscripions(self, signer_or_signature: str, _raise: bool = True) -> List[Plan]:
        """
        Returns all active subscriptions for either 'signer' or the user who signed 'signature'
        """
        signer = signatures.get_msg_signer(signer_or_signature)
        active_subscriptions = [sub for subs in await asyncio.gather(*[subscriber.get_active_subscripions(signer, sync=False) for subscriber in self.subscribers]) for sub in subs if sub]
        if not active_subscriptions and _raise is True:
            raise NoActiveSubscriptions(signer)
        return active_subscriptions
    
    ##############
    # Validation #
    ##############
    
    async def validate_signature(self, signature: str) -> List[Plan]:
        """
        Returns all active subscriptions for the user who signed 'signature'
        """
        try:
            return await self.get_active_subscripions(signature)
        except NoActiveSubscriptions:
            raise SignatureNotAuthorized(self, signature)

    async def validate_signature_from_headers(self, headers: Dict[str, Any]) -> List[int]:
        if await self._should_use_escape_hatch(headers):
            # Escape hatch activated. Reuest will pass thru ySubs
            return True
        if "X-Signature" not in headers:
            raise SignatureNotProvided(self, headers)
        return await self.validate_signature(headers["X-Signature"])
    
    ###############
    # Middlewares #
    ###############
    
    @property
    def fastapi_middleware(self):
        try:
            from fastapi.middleware import Middleware
            from fastapi.responses import JSONResponse
        except ImportError:
            raise ImportError("fastapi is not installed.")
        return Middleware(self._get_starlette_middleware(JSONResponse))
    
    @property
    def starlette_middleware(self):
        try:
            from starlette.responses import JSONResponse
        except ImportError:
            raise ImportError("starlette is not installed.")
        return self._get_starlette_middleware(JSONResponse)
    
    ############
    # Internal #
    ############
    
    def _get_starlette_middleware(self, response_cls: type):
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import HTTPConnection
        class SignatureMiddleware(BaseHTTPMiddleware):
            async def dispatch(self_mw, request: HTTPConnection, call_next: Callable[[HTTPConnection], T]) -> T:
                try:
                    await self.validate_signature_from_headers(request.headers)
                except SignatureError as e:
                    return response_cls(status_code=401, content={'message': str(e)})
                return await call_next(request)
        return SignatureMiddleware
    
    async def _should_use_escape_hatch(self, headers: dict) -> bool:
        if self._headers_escape_hatch is None:
            return False
        hatch = self._headers_escape_hatch(headers)
        if isawaitable(hatch):
            hatch = await hatch
        if isinstance(hatch, bool):
            return hatch
        raise TypeError(f"_headers_escape_hatch must return a boolean value or an awaitable that returns a boolean when awaited. Yours returned {hatch}")
