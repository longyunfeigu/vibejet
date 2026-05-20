# backend

vibejet 后端：FastAPI + 异步 SQLAlchemy + gRPC，采用 **DDD + 六边形架构** 分层。

## 依赖方向

```
api/ → application/ → domain/ ← infrastructure/
```

- `domain/` 纯业务逻辑，**不得**导入框架、ORM、HTTP
- `infrastructure/` 实现 `domain/` 与 `application/ports/` 中定义的接口
- `api/` 仅处理 I/O 绑定与依赖注入

## 目录结构

| 目录 | 职责 |
|------|------|
| `api/` | FastAPI 路由、中间件、依赖注入 |
| `application/` | 用例编排、DTO、ports |
| `domain/` | 实体、聚合、领域服务、仓储接口、领域事件 |
| `infrastructure/` | ORM 模型、仓储实现、外部服务适配器、Celery 任务 |
| `core/` | 配置、日志、异常、统一响应 |
| `shared/` | 业务码、常量、提示词等跨切面 |
| `grpc_app/` | gRPC 运行时与 proto stub |
| `alembic/` | 数据库迁移（详见 [`alembic/README.md`](alembic/README.md)） |
| `locales/` | 国际化翻译（详见 [`locales/README.md`](locales/README.md)） |
| `tests/` | pytest 测试用例 |
| `scripts/` | proto 生成、Celery 启动等辅助脚本 |

## 入口

- REST: `python main.py` → `http://localhost:8000`（`/docs`、`/redoc`）
- gRPC: `python grpc_main.py`

## 本地开发

依赖：Python 3.11、[uv](https://github.com/astral-sh/uv)。

```bash
cd backend
cp env.example .env          # 编辑 SECRET_KEY、DATABASE__URL 等

uv venv --python 3.11 .venv
source .venv/bin/activate
uv sync --extra dev

uv run uvicorn main:app --reload
```

## 常用命令

```bash
# 测试
uv run pytest tests/ -v
uv run pytest tests/ --cov=. --cov-report=term-missing

# Lint / 类型 / 安全
uv run black . && uv run isort . && uv run flake8 .
uv run mypy .
uv run bandit -r . -c pyproject.toml

# 数据库迁移
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head

# Proto 生成
bash scripts/gen_protos.sh

# i18n
uv run pybabel extract -F babel.cfg -k _l -o locales/messages.pot .
uv run pybabel update -i locales/messages.pot -d locales/
uv run pybabel compile -d locales/
```

## 配置

使用 Pydantic Settings v2，支持嵌套环境变量（`__` 分隔）。完整字段见 `env.example`。

```bash
APP_NAME=vibejet
DEBUG=false
ENVIRONMENT=development
SECRET_KEY=change-me
DATABASE__URL=postgresql+asyncpg://user:password@localhost:5432/dbname
REDIS__URL=redis://localhost:6379/0
STORAGE__TYPE=local
```

## 参考

- 仓库根 [`README.md`](../README.md)：项目总览与基线策略
- [`docs/project/architecture.md`](../docs/project/architecture.md)：架构详解
- [`docs/reference/guides/review-checklist-python-fastapi.md`](../docs/reference/guides/review-checklist-python-fastapi.md)：评审清单
- 根 [`CLAUDE.md`](../CLAUDE.md)：分层约束与开发流程
