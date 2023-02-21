
from eth_account import Account

from ysubs import _config


def get_msg_signer(signature: str) -> str:
    return Account.recover_message(_config.UNSIGNED_MESSAGE, signature=signature)
