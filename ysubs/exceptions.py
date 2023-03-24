
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ysubs.ysubs import ySubs
    
class SignatureError(Exception):
    pass

class SignatureNotProvided(SignatureError):
    def __init__(self, ysubs: "ySubs", headers: dict):
        super().__init__(f'You must subscribe to a plan at {ysubs.url} and pass the provided signature as a header param "X-Signature".', headers)

class SignatureNotAuthorized(SignatureError):
    def __init__(self, ysubs: "ySubs", signature: str):
        super().__init__(f"Signature {signature} does not have an active subscription. Please purchase one at {ysubs.url}")

class NoActiveSubscriptions(Exception):
    def __init__(self, signer: str):
        super().__init__(f"No active subscriptions for {signer}")
