import asyncio
from functools import lru_cache
from inspect import isawaitable
from typing import (Any, Awaitable, Callable, Dict, Iterable, List, Optional,
                    Set, TypeVar, Union)

from a_sync import ASyncGenericBase
from brownie import convert
from brownie.convert.datatypes import EthAddress
from eth_typing import ChecksumAddress

from ysubs.exceptions import (BadInput, NoActiveSubscriptions, SignatureError,
                              SignatureNotAuthorized, SignatureNotProvided,
                              SignerInvalid, SignerNotProvided,
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

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None


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
        self.free_trial = FreeTrial(free_trial_rate_limit) if free_trial_rate_limit else None
        
        if _request_escape_hatch is not None and not callable(_request_escape_hatch):
            msg = "_request_escape_hatch must a callable that accepts a Request and returns either:\n\n"
            msg += " - a boolean value\n"
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
        self._checksummed: Set[EthAddress] = set()
    
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
        if not active_subscriptions:
            if self.free_trial is not None:
                active_subscriptions.append(self._get_free_trial(signer))
            elif _raise is True:
                raise NoActiveSubscriptions(signer)
        return active_subscriptions
    
    ##############
    # Validation #
    ##############
    
    async def get_limiter(self, signer: str, signature: str) -> SubscriptionsLimiter:
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
        if "X-Signer" not in headers or not headers["X-Signer"]:
            raise SignerNotProvided(self, headers)
        if "X-Signature" not in headers or not headers["X-Signature"]:
            raise SignatureNotProvided(self, headers)
        return await self.validate_signature(self._checksum(headers["X-Signer"]), headers["X-Signature"], sync=False)
    
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
                if self_mw.__is_documenation(request.url.path) or await self._should_use_requests_escape_hatch(request):
                    return await call_next(request)
                try:
                    user_limiter = await self.validate_signature_from_headers(request.headers, sync=False)
                    if user_limiter is True:
                        return await call_next(request)
                    if sentry_sdk:
                        sentry_sdk.set_user({'id': request.headers["X-Signer"]})
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

    def _checksum(self, signer: str) -> EthAddress:
        if signer not in self._checksummed:
            try:
                signer = convert.to_address(signer)
            except ValueError as e:
                if "is not a valid ETH address" not in e:
                    raise e
                raise SignerInvalid(signer)
            self._checksummed.add(signer)
        return signer