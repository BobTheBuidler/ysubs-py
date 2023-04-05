
from typing import Optional

from eth_account.messages import encode_defunct

from ysubs import _config
from ysubs.exceptions import NoMessageSpecified, SignatureInvalid
from ysubs.utils import signatures


class Plan:
    def __init__(
        self,
        price: int,
        rate_limit: int,
        time_interval: str,
        is_active: bool,
        name: Optional[str] = None,  # Not all subscribers support names.
    ) -> None:
        self.name = name
        self.price = price
        self.requests_per_minute = rate_limit
        self.seconds_per_request = rate_limit / 60
    
    def __repr__(self) -> str:
        return f"<Plan {self.name}>" if self.name else f"<Unnamed Plan>"


class FreeTrial(Plan):
    def __init__(self, rate_limit: int, unsigned_message: Optional[str] = None):
        super().__init__(name="Free Trial", price=0, rate_limit=rate_limit, time_interval="Not Implemented", is_active=True)
        try:
            self.unsigned_msg = encode_defunct(text=unsigned_message or _config.unsigned_trial_message)
        except TypeError as e:
            if str(e) == "Exactly one of the passed values can be specified. Instead, values were: (None,), {'hexstr': None, 'text': None}":
                raise NoMessageSpecified("You must provide the unsigned message to use for your free trial, either with the 'unsigned_message' kwarg or the 'YSUBS_FREE_RIAL_MESSAGE' env var.")
            raise e
    def confirm_signer(self, signer, signature: str) -> str:
        try:
            signatures.validate_signer_with_signature(signer, signature, message=self.unsigned_msg)
            return True
        except SignatureInvalid:
            return False
    