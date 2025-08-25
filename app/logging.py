import os
from dotenv import load_dotenv
import logging

ENV = os.getenv('ENV', 'dev')

LOG_LEVEL = logging.DEBUG if ENV == 'development' else logging.INFO
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
LOG_FILE = os.path.join(os.path.dirname(__file__), 'app.log')

# Configure root logger
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger("stock-alert-system")

def log_info(message, *args, **kwargs):
    logger.info(message, *args, **kwargs)

def log_warning(message, *args, **kwargs):
    logger.warning(message, *args, **kwargs)

def log_error(message, *args, **kwargs):
    logger.error(message, *args, **kwargs)

def log_debug(message, *args, **kwargs):
    logger.debug(message, *args, **kwargs)

def log_data(label, data):
    """
    Log structured data with a label.
    """
    logger.info("%s: %s", label, repr(data))