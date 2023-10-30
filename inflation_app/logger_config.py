import logging
import os

logger = logging.getLogger(__name__)

logger.setLevel(logging.WARNING)

log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, "inflation_app.log")
handler = logging.FileHandler(log_file)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)
