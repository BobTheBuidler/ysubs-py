import asyncio
from inspect import isawaitable
from typing import (Any, Awaitable, Callable, Dict, Iterable, List, Optional,
                    TypeVar, Union)

from a_sync import ASyncGenericBase
from eth_typing import ChecksumAddress
from functools import lru_cache

from ysubs.exceptions import (BadInput, NoActiveSubscriptions, SignatureError,SignatureInvalid,
                              SignatureNotAuthorized, SignatureNotProvided,
                              TooManyRequests)
from ysubs.plan import FreeTrial, Plan
from ysubs.subscriber import Subscriber
from ysubs.subscription import Subscription, SubscriptionsLimiter
from ysubs.utils import signatures

T = TypeVar('T')

EscapeHatch = Union[
    Callable[[T], bool], 
    Callable[[T], Awaitable[bool]]
]

RequestEscapeHatch = EscapeHatch["Request"]
HeadersEscapeHatch = EscapeHatch[dict]


class ySubs(ASyncGenericBase):
    def __init__(
        self,
        addresses: Iterable[ChecksumAddress],
        url: str,
        asynchronous: bool = False,
        free_trial_rate_limit: Optional[int] = None,
        _request_escape_hatch: Optional[RequestEscapeHatch] = None,
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
        
        if free_trial_rate_limit is not None and not isinstance(free_trial_rate_limit, int):
            raise TypeError(f"'free_trial_rate_limit' must be an integer or 'None'. You passed {free_trial_rate_limit}")
        self.free_trial = FreeTrial(free_trial_rate_limit)
        
        if _request_escape_hatch is not None and not callable(_request_escape_hatch):
            msg = "_request_escape_hatch must a callable that accepts a Request and returns either:\n\n"
        self.free_trial = FreeTrial(free_trial_rate_limit) if free_trial_rate_limit else None
            msg += " - an awaitable that returns a boolean when awaited.\n\n"
            msg += f"You passed {_headers_escape_hatch}"
            raise TypeError(msg)
        self._request_escape_hatch = _request_escape_hatch
        
        if _headers_escape_hatch is not None and not callable(_headers_escape_hatch):
            msg = "_headers_escape_hatch must a callable that accepts a dict and returns either:\n\n"
            msg += " - a boolean value\n"
            msg += " - an awaitable that returns a boolean when awaited.\n\n"
            msg += f"You passed {_headers_escape_hatch}"
            raise TypeError(msg)
        self._headers_escape_hatch = _headers_escape_hatch
        
        self.subscribers = [Subscriber(address, asynchronous=asynchronous) for address in addresses]
        self._free_trials: Dict[str, Subscription] = {}
    
    ##########
    # System #
    ##########
    
    async def get_all_plans(self) -> Dict[Subscriber, List[Plan]]:
        """
        Returns all Plans defined on each Subscriber.
        """
        plans = await asyncio.gather(*[subscriber.get_all_plans(sync=False) for subscriber in self.subscribers])
        return dict(zip(self.subscribers, plans))

    @lru_cache(maxsize=None)
    def _get_free_trial(self, signer: str) -> Subscription:
        return Subscription(signer, self.free_trial)
    
    #################
    # Informational #
    #################
    
    async def get_active_subscripions(self, signer: str, _raise: bool = True) -> List[Subscription]:
        """
        Returns all active subscriptions for either 'signer' or the user who signed 'signature'
        """
        active_subscriptions = [sub for subs in await asyncio.gather(*[subscriber.get_active_subscripions(signer, sync=False) for subscriber in self.subscribers]) for sub in subs if sub]
        if not active_subscriptions and _raise is True:
            raise NoActiveSubscriptions(signer)
        return active_subscriptions
    
    ##############
    # Validation #
    ##############
    
    async def get_limiter(self, signer: str, signature: str) -> SubscriptionsLimiter:
        if self.free_trial.confirm_signer(signer, signature):
            return SubscriptionsLimiter([self._get_free_trial(signer)])
        signatures.validate_signer_with_signature(signer, signature)
        return SubscriptionsLimiter(await self.get_active_subscripions(signer, sync=False))
    
    async def validate_signature(self, signer: str, signature: str) -> SubscriptionsLimiter:
        """
        Returns all active subscriptions for the user who signed 'signature'
        """
        try:
            return await self.get_limiter(signer, signature, sync=False)
        except NoActiveSubscriptions:
            raise SignatureNotAuthorized(self, signature)

    async def validate_signature_from_headers(self, headers: Dict[str, Any]) -> SubscriptionsLimiter:
        if await self._should_use_headers_escape_hatch(headers):
            # Escape hatch activated. Reuest will pass thru ySubs
            return True
        if "X-Signature" not in headers:
            raise SignatureNotProvided(self, headers)
        return await self.validate_signature(headers["X-Signer"], headers["X-Signature"], sync=False)
    
    ###############
    # Middlewares #
    ###############
    
    @property
    def fastapi_middleware(self):
        """Fastapi middleware is just a wrapper around a starlette middleware that returns a JSONResponse defined by fastapi instead of by starlette."""
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
        # NOTE: We don't want to block any files used for the documentation pages.
        do_not_block = ["/favicon.ico", "/openapi.json"]
        class SignatureMiddleware(BaseHTTPMiddleware):
            async def dispatch(self_mw, request: HTTPConnection, call_next: Callable[[HTTPConnection], T]) -> T:
                if not self_mw.__is_documenation(request.url.path) and not await self._should_use_requests_escape_hatch(request):
                    try:
                        user_limiter = await self.validate_signature_from_headers(request.headers)
                        with user_limiter:
                            return await call_next(request)
                    except BadInput as e:
                        return response_cls(status_code=400, content={'message': str(e)})
                    except (SignatureError, TooManyRequests) as e:
                        return response_cls(status_code=401, content={'message': str(e)})
            def __is_documenation(self_mw, path: str):
                """We don't want to block calls to the documentation pages."""
                return path.startswith("/docs") or path in do_not_block
        return SignatureMiddleware
    
    async def _should_use_requests_escape_hatch(self, request: "Request") -> bool:
        if self._request_escape_hatch is None:
            return False
        hatch = self._request_escape_hatch(request)
        if isawaitable(hatch):
            hatch = await hatch
        if isinstance(hatch, bool):
            return hatch
        raise TypeError(f"_request_escape_hatch must return a boolean value or an awaitable that returns a boolean when awaited. Yours returned {hatch}")
    
    async def _should_use_headers_escape_hatch(self, headers: dict) -> bool:
        if self._headers_escape_hatch is None:
            return False
        hatch = self._headers_escape_hatch(headers)
        if isawaitable(hatch):
            hatch = await hatch
        if isinstance(hatch, bool):
            return hatch
        raise TypeError(f"_headers_escape_hatch must return a boolean value or an awaitable that returns a boolean when awaited. Yours returned {hatch}")
