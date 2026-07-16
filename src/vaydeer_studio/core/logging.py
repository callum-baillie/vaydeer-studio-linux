"""Small, opt-in structured logging setup shared by the CLI, service, and UI."""

from __future__ import annotations

import logging
import os


def configure_logging(*, verbose: bool = False, level: str | None = None) -> None:
    """Configure one process-wide safe diagnostic logger without host identifiers."""

    configured_level = os.environ.get("VAYDEER_STUDIO_LOG_LEVEL", "").upper()
    level_name = (level or ("DEBUG" if verbose else configured_level or "WARNING")).upper()
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    numeric_level = levels.get(level_name, logging.WARNING)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
