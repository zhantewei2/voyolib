import logging
import tempfile
from pathlib import Path

from voyo.utils.logger.logger import init_logger, configure_framework_loggers


def test_init_logger():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"
        init_logger(log_dir=log_dir, max_bytes=1024, backup_count=3)

        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 3

        logger = logging.getLogger("test.logger")
        logger.info("hello info")
        logger.warning("hello warning")

        info_log = log_dir / "info" / "app.log"
        warning_log = log_dir / "warning" / "warning.log"
        assert info_log.exists()
        assert warning_log.exists()

        info_content = info_log.read_text()
        assert "hello info" in info_content
        assert "hello warning" in info_content

        warning_content = warning_log.read_text()
        assert "hello warning" in warning_content
        assert "hello info" not in warning_content

    print("test_init_logger passed")


def test_configure_framework_loggers():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_logger(log_dir=tmpdir + "/logs")
        configure_framework_loggers(level=logging.DEBUG)

        for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
            logger = logging.getLogger(name)
            assert logger.propagate is False
            assert logger.level == logging.DEBUG
            assert len(logger.handlers) == 3

    print("test_configure_framework_loggers passed")


def test_size_rollover():
    from voyo.utils.logger.timed_size_rotating_handler import TimedAndSizeRotatingFileHandler

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "app.log"
        handler = TimedAndSizeRotatingFileHandler(
            filename=log_file,
            when="midnight",
            max_bytes=200,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger = logging.getLogger("test.rollover")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        for i in range(20):
            logger.info("x" * 50)

        handler.close()
        rotated = list(Path(tmpdir).glob("app*.log"))
        assert len(rotated) > 1, f"expected rollover, got {rotated}"

    print("test_size_rollover passed")


if __name__ == "__main__":
    test_init_logger()
    test_configure_framework_loggers()
    test_size_rollover()
    print("\nAll tests passed.")
