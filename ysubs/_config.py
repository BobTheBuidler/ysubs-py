import logging
import os

from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)

# Specify the unsigned message you will use for your application by setting the YSUBS_UNSIGNED_MESSAGE environment variable.
default_message = "I am verifying my ownership of this wallet."
unsigned_message = os.environ.get("YSUBS_UNSIGNED_MESSAGE", default_message)
logger.info(f'unsigned message: {unsigned_message}')
UNSIGNED_MESSAGE = encode_defunct(text=unsigned_message)

# Specify for how long a validated signaure should remain cached, in seconds
VALIDATION_INTERVAL = int(os.environ.get("YSUBS_VALIDATION_INTERVAL", 60 * 5))

# Specify the file path for the creation of local ysubs database
DB_PATH = os.environ.get("YSUBS_DB_PATH", '/.ysubs/ysubs.sqlite')
