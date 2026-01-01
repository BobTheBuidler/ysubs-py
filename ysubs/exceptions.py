from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ysubs.ysubs import ySubs


class SignatureError(Exception):
    pass


class SignerNotProvided(SignatureError):
    def __init__(self, ysubs: "ySubs", headers: dict) -> None:
        msg = f'You must subscribe to a plan at {ysubs.url} and pass the wallet address that signed the msg as header param "X-Signer\n\n"'
        msg += f"Your headers: {headers}"
        super().__init__(msg)


class SignerInvalid(SignatureError):
    def __init__(self, signer: str) -> None:
        msg = f"The X-Signer header you provided ({signer}) is not a valid address."
        super().__init__(msg)


class SignatureNotProvided(SignatureError):
    def __init__(self, ysubs: "ySubs", headers: dict) -> None:
        msg = f'You must subscribe to a plan at {ysubs.url} and pass the provided signature as header param "X-Signature\n\n"'
        msg += f"Your headers: {headers}"
        super().__init__(msg)


class SignatureNotAuthorized(SignatureError):
    def __init__(self, ysubs: "ySubs", signature: str) -> None:
        f"Signature {signature} does not have an active subscription. Please purchase one at {ysubs.url}"
        super().__init__(msg)


class SignatureInvalid(SignatureError):
    def __init__(self, signer: str, signature: str) -> None:
        super().__init__(f"Signature {signature} is not valid for signer {signer}")


class NoActiveSubscriptions(Exception):
    def __init__(self, signer: str) -> None:
        super().__init__(f"No active subscriptions for {signer}")


class BadInput(ValueError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # NOTE Sometimes we just pass in an Exception as input here and want to convert it to a string.
        new_args = [str(arg) if isinstance(arg, Exception) else arg for arg in args]
        super().__init__(*new_args, **kwargs)


class MalformedSignature(BadInput):
    pass


class TooManyRequests(Exception):
    def __init__(self, time_til_next_request: float) -> None:
        msg = f"You can make your next request in {round(time_til_next_request, 2)} seconds."
        super().__init__(msg)


class NoMessageSpecified(ValueError):
    pass
