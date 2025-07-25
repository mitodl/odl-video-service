"""Configure structured logging for our application"""

import logging

import structlog
from structlog_sentry import SentryProcessor

from odl_video import settings

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), format="%(message)s")

structlog_processors_per_debug = {
    True: [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    False: [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        SentryProcessor(
            level=logging.ERROR,
            tag_keys=[
                "environment",
                "level",
                "logger",
                "runtime",
                "server_name",
                "video_id",
                "video_hexkey",
                "s3_object_key",
                "filename",
                "youtubevideo_id",
                "youtubevideo_video_id",
                "video_status",
            ],
        ),
        structlog.processors.JSONRenderer(),
    ],
}

structlog.configure(
    processors=structlog_processors_per_debug[settings.DEBUG],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)


def getLogger(name):
    """Return a logger with the given name"""
    logger = structlog.get_logger(name)
    if settings.LOG_FILE:
        logger.addHandler(logging.FileHandler(settings.LOG_FILE))
    return logger
