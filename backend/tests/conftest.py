# input: 进程环境变量
# output: pytest 采集前的强制环境变量兜底（SECRET_KEY 须过弱值/长度校验）
# pos: 后端测试 - pytest bootstrap；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Pytest bootstrap configuration.

Ensure mandatory environment variables are set before test collection
and module imports that depend on application settings.
"""

import os

# Mandatory secret key for settings validation (must pass weak-value + min-length checks)
os.environ.setdefault("SECRET_KEY", "unit-test-only-secret-key-0123456789abcdef")
