"""
worker 启动入口。
用法：
  python worker.py                # 默认消费 normal
  python worker.py normal beat    # 消费 normal 和 beat
"""
import sys
from app import celery

if __name__ == "__main__":
    queues = sys.argv[1:] or ["normal"]
    argv = [
        "worker",
        "-A", "app:celery",
        "-l", "info",
        "-Q", ",".join(queues),
        "--concurrency=2",
    ]
    celery.worker_main(argv)