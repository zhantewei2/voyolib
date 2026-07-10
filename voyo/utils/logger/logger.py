import logging
import os
from pathlib import Path

from .timed_size_rotating_handler import TimedAndSizeRotatingFileHandler

DEFAULT_LOG_DIR = Path.cwd() / "logs"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 30
DEFAULT_WARNING_BACKUP_COUNT = 60
DEFAULT_INTERVAL = "midnight"
DEFAULT_LEVEL = logging.INFO

_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def configure_framework_loggers(level: int=DEFAULT_LEVEL) -> None:
    root = logging.getLogger()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(level)
        for handler in root.handlers:
            logger.addHandler(handler)


def init_logger(
    log_dir: Path | str = DEFAULT_LOG_DIR,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    warning_backup_count: int = DEFAULT_WARNING_BACKUP_COUNT,
    interval: str = DEFAULT_INTERVAL,
    level: int = DEFAULT_LEVEL,
) -> None:
    """初始化全局日志，替换默认 handler 为按时间+大小双规则 rotate 的文件 handler。

    应在应用启动时手动调用一次，之后所有 logging.getLogger() 均使用此配置。
    """
    log_dir = Path(log_dir)
    info_dir = log_dir / "info"
    warning_dir = log_dir / "warning"
    info_dir.mkdir(parents=True, exist_ok=True)
    warning_dir.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    file_handler = TimedAndSizeRotatingFileHandler(
        filename=info_dir / "app.log",
        when=interval,
        backupCount=backup_count,
        max_bytes=max_bytes,
        encoding="utf-8",
    )
    warning_file_handler = TimedAndSizeRotatingFileHandler(
        filename=warning_dir / "warning.log",
        when=interval,
        backupCount=warning_backup_count,
        max_bytes=max_bytes,
        encoding="utf-8",
    )

    for handler in (console_handler, file_handler, warning_file_handler):
        handler.setFormatter(_formatter)
    file_handler.setLevel(logging.INFO)
    warning_file_handler.setLevel(logging.WARNING)

    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler, warning_file_handler],
        force=True,
    )
    
    configure_framework_loggers(level)



