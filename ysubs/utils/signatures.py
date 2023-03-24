
import binascii

import eth_keys.validation
from brownie import convert
from eth_account import Account

from ysubs import _config
from ysubs.exceptions import MalformedSignature


def get_msg_signer(signer_or_signature: str) -> str:
    try:
        return convert.to_address(signer_or_signature)
    except ValueError as e:
        if "is not a valid ETH address" not in str(e):
            raise e
        return get_signer_from_signature(signer_or_signature)
    
def get_signer_from_signature(signature: str) -> str:
    try:
        return Account.recover_message(_config.UNSIGNED_MESSAGE, signature=signature)
    except binascii.Error as e:
        raise MalformedSignature(e)
    except eth_keys.validation.ValidationError as e:
        if "Unexpected recoverable signature length:" in str(e):
            raise MalformedSignature(f"The signature you provided does not have the correct length.")
        raise MalformedSignature(e)
