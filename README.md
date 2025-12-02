# 项目结构
```
Simulation/
├─ docs/
├─ src/
│  ├─ CProgram/
│  │  └─ radar/
│  └─ PythonProgram/
│     └─ radar/
│        ├─ radar_interface_simulator.py
│        └─ requirements.md
├─ .gitignore
└─ README.md

```


在文件夹中，当前实现仅设置了初始值但缺少完整的交互逻辑。需要按照以下要求完善：

1. 初始值设置后，应自动触发以下交互逻辑：
   - 数据验证：检查初始值是否符合业务规则和数据类型要求
   - 状态更新：根据初始值自动更新相关组件的状态
   - 数据联动：触发相关联的数据计算或更新流程

2. 具体实现要求：
   - 为每个初始值添加对应的响应式处理逻辑
   - 建立数据变更监听机制，确保值变化时能正确触发后续处理
   - 实现必要的错误处理机制，防止无效初始值导致系统异常

3. 测试验证标准：
   - 验证设置初始值后所有相关数据是否同步更新
   - 检查各交互逻辑是否按预期执行
   - 确保系统在异常初始值情况下的健壮性



```python
import time
import socket
from threading import Lock

class TokenBucketLimiter:
    def __init__(self, rate_kbps, bucket_seconds=1.0):
        """
        rate_kbps: 限制带宽（Kbps）
        bucket_seconds: 突发缓冲区大小（以秒为单位）
                        bucket_size = rate * bucket_seconds
        """
        # 转为 bytes/sec
        self.rate_bytes = (rate_kbps * 1000) / 8
        self.bucket_size = self.rate_bytes * bucket_seconds
        
        self.tokens = self.bucket_size  # 初始令牌满
        self.timestamp = time.time()
        self.lock = Lock()

    def consume(self, amount):
        """
        需要消耗 amount 字节令牌（阻塞直到可发送）
        """
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.timestamp

                # 按时间补充令牌
                self.tokens = min(self.bucket_size, self.tokens + elapsed * self.rate_bytes)
                self.timestamp = now

                if self.tokens >= amount:
                    self.tokens -= amount
                    return  # 允许发送

                # 需要等待更多令牌生成
                needed = amount - self.tokens
                wait_time = needed / self.rate_bytes

            time.sleep(wait_time)


class LimitedUDPSocket:
    def __init__(self, max_bandwidth_kbps=1000, burst_seconds=1.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.limiter = TokenBucketLimiter(max_bandwidth_kbps, burst_seconds)

    def sendto(self, data, address):
        self.limiter.consume(len(data))
        return self.sock.sendto(data, address)

    def close(self):
        self.sock.close()

```



使用示例

```python
udp = LimitedUDPSocket(max_bandwidth_kbps=500)  # 限制为 500 Kbps

while True:
    udp.sendto(b"HelloWorld" * 10, ("127.0.0.1", 9999))

```







## 动态监测网络实际宽带

```python
import time
import socket
from threading import Lock

class AdaptiveTokenBucket:
    def __init__(self, limit_ratio=0.3, measure_window=1.0):
        """
        limit_ratio: 限制比例 (0.3 = 限制到 30%)
        measure_window: 测速时间窗口（秒）
        """
        self.limit_ratio = limit_ratio
        self.measure_window = measure_window
        
        self.token_rate = None   # 实时更新的令牌速率（bytes/sec）
        self.bucket_size = None  # 动态桶大小
        
        self.tokens = 0
        self.timestamp = time.time()
        self.lock = Lock()

        self.byte_history = []  # (time, bytes)
    
    def update_rate(self):
        """根据最近 measure_window 秒的数据，计算带宽并调整令牌桶"""
        now = time.time()
        # 删除超时数据
        self.byte_history = [(t, b) for (t, b) in self.byte_history if now - t <= self.measure_window]

        total_bytes = sum(b for (_, b) in self.byte_history)
        measured_rate = total_bytes / self.measure_window   # bytes/sec

        if measured_rate <= 0:
            return  # 暂无数据，不更新

        # 限制目标 = 实际速率 × 30%
        new_rate = measured_rate * self.limit_ratio

        # 若第一次或变动较大，则更新 token 参数
        if self.token_rate is None or abs(new_rate - self.token_rate) / self.token_rate > 0.1:
            self.token_rate = new_rate
            self.bucket_size = new_rate  # 允许 1 秒突发
            self.tokens = self.bucket_size  # 重置令牌
            print(f"[AutoLimit] Measured={measured_rate/1e6:.2f} MB/s  Limited={new_rate/1e6:.2f} MB/s")

    def consume(self, amount):
        # 记录带宽用于测量
        self.byte_history.append((time.time(), amount))
        self.update_rate()

        # 若还没测到速率，默认立即允许
        if self.token_rate is None:
            return
        
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.timestamp
                self.timestamp = now

                # 添加令牌
                self.tokens = min(self.bucket_size, self.tokens + elapsed * self.token_rate)

                if self.tokens >= amount:
                    self.tokens -= amount
                    return  # 可以发送

                # 需要等待
                lack = amount - self.tokens
                wait_time = lack / self.token_rate

            time.sleep(wait_time)


class AdaptiveLimitedUDPSocket:
    def __init__(self, limit_ratio=0.3):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.limiter = AdaptiveTokenBucket(limit_ratio)

    def sendto(self, data, address):
        self.limiter.consume(len(data))
        return self.sock.sendto(data, address)

    def close(self):
        self.sock.close()

```

```python
udp = AdaptiveLimitedUDPSocket(limit_ratio=0.3)  # 限制到 30%

while True:
    udp.sendto(b"x" * 1400, ("127.0.0.1", 9000))

```

