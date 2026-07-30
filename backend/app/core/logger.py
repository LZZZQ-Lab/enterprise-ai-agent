import logging
import sys

from app.config import settings


if hasattr(sys.stdout, "reconfigure"):

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):

    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


logging.basicConfig(

    level=settings.LOG_LEVEL,

    format="%(asctime)s | %(levelname)s | %(message)s",

    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(settings.APP_NAME)