
import binascii
from typing import Optional

import eth_keys.validation
from eth_account import Account

from ysubs import _config
from ysubs.exceptions import MalformedSignature, SignatureInvalid


def validate_signer_with_signature(signer: str, signature: str) -> None:
    try:
        if signer == Account.recover_message(_config.UNSIGNED_MESSAGE, signature=signature):
            return
        raise SignatureInvalid(signer, signature)
    except binascii.Error as e:
        raise MalformedSignature(e)
    except eth_keys.validation.ValidationError as e:
        if "Unexpected recoverable signature length:" in str(e):
            raise MalformedSignature(f"The signature you provided does not have the correct length.")
        raise MalformedSignature(e)
