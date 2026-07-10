import os
import time
from logging.handlers import TimedRotatingFileHandler


class TimedAndSizeRotatingFileHandler(TimedRotatingFileHandler):
    """按时间或文件大小双重条件 rotate，满足任一即触发。"""

    def __init__(self, filename, when='h', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False, atTime=None,
                 max_bytes=0):
        super().__init__(filename, when, interval, backupCount,
                         encoding, delay, utc, atTime)
        self.max_bytes = max_bytes

    def shouldRollover(self, record):
        if super().shouldRollover(record):
            return True
        if self.max_bytes > 0:
            self.stream.seek(0, 2)
            if self.stream.tell() >= self.max_bytes:
                return True
        return False

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        current_time = int(self.rolloverAt)
        new_rollover_at = self.computeRollover(current_time)

        # 大小触发：时间还没到，加数字后缀避免覆盖
        if new_rollover_at > int(time.time()):
            base, ext = os.path.splitext(self.baseFilename)
            dfn = f"{base}.1{ext}"
            num = 1
            while os.path.exists(dfn):
                num += 1
                dfn = f"{base}.{num}{ext}"
        else:
            dfn = self.rotation_filename(self.baseFilename)

        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        self.rolloverAt = new_rollover_at

        if not self.delay:
            self.stream = self._open()
