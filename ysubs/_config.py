
import logging
import os

from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)

# Specify the unsigned message you will use for your application by setting the YSUBS_UNSIGNED_MESSAGE environment variable.
default_message = "I am verifying my ownership of this wallet."
unsigned_message = os.environ.get("YSUBS_UNSIGNED_MESSAGE", default_message)
logger.info(f'unsigned message: {unsigned_message}')
UNSIGNED_MESSAGE = encode_defunct(text=unsigned_message)
