import threading
import time
import random


class YoUnique:
    lock = threading.Lock()
    pre_timestamp = 0
    index = 0

    def _get_rng(self) -> str:
        """线程安全的随机数生成器（如需保留随机数）"""
        i = random.randint(0, 99)
        return f"{i:02d}"

    def get_uid(self):
        while True:
            with self.lock:
                current_timestamp = int(time.time() * 1000)
                if current_timestamp == self.pre_timestamp:
                    # 同一毫秒内索引限制在 0-999，避免溢出
                    if self.index < 999:
                        self.index += 1
                        index = self.index
                        timestamp = current_timestamp
                        break
                else:
                    # 新毫秒重置索引
                    self.index = 0
                    self.pre_timestamp = current_timestamp
                    index = 0
                    timestamp = current_timestamp
                    break
            # 索引满时释放锁等待，避免阻塞其他线程
            time.sleep(0.001)

        # 生成 3 位索引（固定长度，确保格式一致）
        mid_str = f"{index:03d}"
        random_str = self._get_rng()
        # 推荐：仅用时间戳 + 索引保证唯一性（无随机数，更稳定）
        return int(f"{timestamp}{mid_str}{random_str}")


yo_unique = YoUnique()
