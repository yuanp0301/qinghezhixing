import logging
from app.logging_conf import configure_logging


def test_configure_logging_sets_level():
    configure_logging("DEBUG")
    assert logging.getLogger("app").level == logging.DEBUG
