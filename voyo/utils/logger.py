import logging


def get_logger(name: str = "voyo") -> logging.Logger:
    return logging.getLogger(name)
