"""Configure structured logging for our application"""
import logging
from structlog_sentry import SentryJsonProcessor
import structlog
from odl_video import settings


logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL),
                    format='%(message)s')

structlog_processors_per_debug = {
    True: [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.dev.ConsoleRenderer()
    ],
    False: [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        SentryJsonProcessor(tag_keys='__all__'),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(),
        structlog.processors.JSONRenderer()
    ]
}

structlog.configure(
    processors=structlog_processors_per_debug[settings.DEBUG],
    logger_factory=structlog.stdlib.LoggerFactory()
)


def getLogger(name):
    """Return a logger with the given name"""
    return structlog.get_logger(name)
