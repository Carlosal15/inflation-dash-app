import logging

logger = logging.getLogger(__name__)

logger.setLevel(logging.WARNING)

handler = logging.FileHandler("inflation_app.log")

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)
