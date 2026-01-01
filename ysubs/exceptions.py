from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ysubs.ysubs import ySubs
    
class SignatureError(Exception):
    pass

class SignerNotProvided(SignatureError):
    def __init__(self, ysubs: "ySubs", headers: dict):
        msg = f'You must subscribe to a plan at {ysubs.url} and pass the wallet address that signed the msg as header param "X-Signer\n\n"'
        msg += f'Your headers: {headers}'
        super().__init__(msg)

class SignerInvalid(SignatureError):
    def __init__(self, signer: str):
        super().__init__(f"The X-Signer header you provided ({signer}) is not a valid address.")
    
class SignatureNotProvided(SignatureError):
    def __init__(self, ysubs: "ySubs", headers: dict):
        msg = f'You must subscribe to a plan at {ysubs.url} and pass the provided signature as header param "X-Signature\n\n"'
        msg += f'Your headers: {headers}'
        super().__init__(msg)

class SignatureNotAuthorized(SignatureError):
    def __init__(self, ysubs: "ySubs", signature: str):
        super().__init__(f"Signature {signature} does not have an active subscription. Please purchase one at {ysubs.url}")

class SignatureInvalid(SignatureError):
    def __init__(self, signer: str, signature: str):
        super().__init__(f"Signature {signature} is not valid for signer {signer}")
    
class NoActiveSubscriptions(Exception):
    def __init__(self, signer: str):
        super().__init__(f"No active subscriptions for {signer}")

class BadInput(ValueError):
    def __init__(self, *args, **kwargs):
        # NOTE Sometimes we just pass in an Exception as input here and want to convert it to a string.
        super().__init__(*[str(arg) if isinstance(arg, Exception) else arg for arg in args], **kwargs)

class MalformedSignature(BadInput):
    pass

class TooManyRequests(Exception):
    def __init__(self, time_til_next_request: float):
        super().__init__(f"You can make your next request in {round(time_til_next_request, 2)} seconds.")

class NoMessageSpecified(ValueError):
    pass