
from eth_account import Account
from eth_account.messages import encode_defunct

MESSAGE = encode_defunct("I am verifying my ownership of this wallet.")

def get_msg_signer(signature: str) -> str:
    return Account.recover_message(MESSAGE, signature=signature)
