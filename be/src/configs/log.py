import logging.config

from configs.settings import settings


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                },
                "verbose": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s "
                    "(%(filename)s:%(lineno)d): %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": settings.log_verbosity,
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": settings.log_level,
            },
            "loggers": {
                "uvicorn": {"propagate": True},
                "uvicorn.access": {"propagate": True},
                "sqlalchemy.engine": {
                    "level": "DEBUG" if settings.db_echo else "WARNING",
                    "propagate": True,
                },
            },
        },
    )
