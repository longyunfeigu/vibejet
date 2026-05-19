# Celery Patterns - Async Task Queue Best Practices

> **Note**: This document provides **generic, reusable patterns**. Replace placeholder names
> (e.g., `resource_id`, `ItemService`, `ProcessorType`) with your domain-specific terms.

---
version: 1.1
last_updated: 2026-01-07
compatible_with:
  - Python 3.11+
  - Celery 5.3+
  - FastAPI 0.100+
  - Redis 7.0+ (as broker)
---

Production-ready Celery patterns for FastAPI microservices, based on project conventions and best practices.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Configuration Patterns](#configuration-patterns)
- [Task Definition Patterns](#task-definition-patterns)
- [Port/Adapter Integration](#portadapter-integration)
- [Task Routing & Prioritization](#task-routing--prioritization)
- [Periodic Tasks (Beat)](#periodic-tasks-beat)
- [Async Task Execution](#async-task-execution)
- [Error Handling & Retry](#error-handling--retry)
- [Idempotency & State Management](#idempotency--state-management)
- [Testing Celery Tasks](#testing-celery-tasks)
- [Monitoring & Observability](#monitoring--observability)
- [Common Pitfalls](#common-pitfalls)
- [Quick Reference](#quick-reference)
- [Customization Guide](#customization-guide)

---

## Architecture Overview

```
Application Layer (Services)
         ↓
    TaskDispatcherPort (Interface)
         ↓
CeleryTaskDispatcher (Implementation)
         ↓
    Celery Broker (Redis)
         ↓
    Worker Process
         ↓
    Task Router → Task Processors
         ↓
    Database / External Services
```

Key Principle: Application layer doesn't know about Celery; it uses a Port interface.

### Directory Structure

```
infrastructure/
└── tasks/
    ├── config/
    │   ├── celery.py        # Celery app configuration
    │   └── beat.py          # Periodic task schedules
    ├── tasks/
    │   ├── task_router.py   # Routes tasks to processors
    │   ├── task_executor.py # Executes single tasks
    │   └── *_processor.py   # Domain-specific processors
    └── utils/
        ├── base_task.py     # Base task class
        └── dispatcher.py    # Dispatcher implementation

application/
└── ports/
    └── task_dispatcher.py   # TaskDispatcherPort interface
```

---

## Configuration Patterns

### Celery Application Setup

```python
# infrastructure/tasks/config/celery.py
from celery import Celery
from kombu import Queue
from core.config import settings

# Explicit task module discovery
CELERY_IMPORTS = (
    "infrastructure.tasks.tasks.task_router",
    "infrastructure.tasks.tasks.task_executor",
    "infrastructure.tasks.tasks.my_processor",
)

celery_app = Celery("my_app")

celery_app.conf.update(
    # Connection - use settings, fallback to env
    broker_url=settings.redis.url,
    result_backend=settings.redis.url,

    # Serialization - JSON for safety and interoperability
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Reliability settings
    task_acks_late=True,              # ACK after completion (enables retry on worker crash)
    task_reject_on_worker_lost=True,  # Requeue on worker lost
    task_track_started=True,          # Track STARTED state

    # Result management
    result_expires=3600,              # Auto-expire results after 1 hour

    # Worker tuning
    worker_prefetch_multiplier=1,     # Fair task distribution

    # Queue configuration
    task_default_queue="default",
    task_default_retry_delay=5,

    # Priority queues
    task_queues=(
        Queue("high"),
        Queue("default"),
        Queue("low"),
    ),

    # Task routing
    task_routes={
        "infrastructure.tasks.tasks.task_router.*": {"queue": "default"},
        "infrastructure.tasks.tasks.task_executor.*": {"queue": "default"},
    },
)

celery_app.conf.imports = CELERY_IMPORTS
```

### Configuration Anti-Patterns

```python
# ❌ NEVER: Hard-coded credentials
broker_url="redis://localhost:6379/0"

# ✅ ALWAYS: Use settings with fallback
broker_url=settings.redis.url or os.getenv("CELERY_BROKER_URL")

# ❌ NEVER: Use pickle serializer (security risk)
task_serializer="pickle"

# ✅ ALWAYS: Use JSON for safety
task_serializer="json"

# ❌ NEVER: autodiscover_tasks with conditional imports
celery_app.autodiscover_tasks()  # May cause import issues

# ✅ ALWAYS: Explicit imports
celery_app.conf.imports = CELERY_IMPORTS
```

---

## Task Definition Patterns

### Base Task Class

Create a base task for unified logging and error handling:

```python
# infrastructure/tasks/utils/base_task.py
from celery import Task
from core.logging_config import get_logger

logger = get_logger(__name__)


class BaseTask(Task):
    """Unified failure logging and hooks for extensions."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "celery_task_failure",
            task_id=task_id,
            task_name=self.name,
            args=args,
            kwargs=kwargs,
            exc=str(exc),
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "celery_task_success",
            task_id=task_id,
            task_name=self.name,
        )
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "celery_task_retry",
            task_id=task_id,
            task_name=self.name,
            exc=str(exc),
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)
```

### Standard Task Definition

```python
# infrastructure/tasks/tasks/my_processor.py
from celery import shared_task
from ..utils.base_task import BaseTask
from core.logging_config import get_logger

logger = get_logger(__name__)


@shared_task(
    bind=True,                    # Access to self (task instance)
    base=BaseTask,                # Use custom base class
    name="my_app.tasks.process_item",  # Explicit name
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),  # Auto-retry for specific exceptions
    retry_backoff=True,           # Exponential backoff
    retry_backoff_max=600,        # Max 10 minutes between retries
    retry_jitter=True,            # Add randomness to prevent thundering herd
)
def process_item(self, item_id: int) -> dict:
    """Process a single item."""
    try:
        result = do_processing(item_id)
        return {"status": "success", "item_id": item_id}
    except TransientError as exc:
        # Manual retry with custom countdown
        raise self.retry(exc=exc, countdown=30)
    except PermanentError as exc:
        # Don't retry, just fail
        logger.error("permanent_failure", item_id=item_id, error=str(exc))
        raise
```

### Task with Timeout

```python
@shared_task(
    bind=True,
    base=BaseTask,
    name="my_app.tasks.long_running_task",
    soft_time_limit=300,   # 5 minutes soft limit (raises SoftTimeLimitExceeded)
    time_limit=360,        # 6 minutes hard limit (kills the task)
)
def long_running_task(self, data: dict) -> dict:
    try:
        return process_large_data(data)
    except SoftTimeLimitExceeded:
        # Graceful cleanup
        cleanup_partial_work()
        raise
```

---

## Port/Adapter Integration

### Define the Port (Interface)

```python
# application/ports/task_dispatcher.py
from abc import ABC, abstractmethod
from typing import Optional
from domain.task import TaskType


class TaskDispatcherPort(ABC):
    """Task dispatcher interface for application layer.

    Note: Customize parameters based on your domain needs.
    Common additions: parent_id, priority, metadata dict, etc.
    """

    @abstractmethod
    def dispatch(
        self,
        task_id: int,
        task_type: Optional[TaskType] = None,
        resource_id: Optional[int] = None,  # Parent resource (customize per domain)
    ) -> bool:
        """Dispatch task to async execution queue.

        Args:
            task_id: The task record ID from database
            task_type: Optional type for routing to specific processors
            resource_id: Optional parent resource ID for context

        Returns:
            True if dispatch succeeded, False otherwise
        """
        ...


class NoOpTaskDispatcher(TaskDispatcherPort):
    """No-op implementation for testing or when async is disabled."""

    def dispatch(self, task_id: int, **kwargs) -> bool:
        return False
```

### Implement the Adapter

```python
# infrastructure/tasks/utils/dispatcher.py
from application.ports.task_dispatcher import TaskDispatcherPort
from domain.task import TaskType
from core.logging_config import get_logger

logger = get_logger(__name__)


class CeleryTaskDispatcher(TaskDispatcherPort):
    """Celery implementation of task dispatcher."""

    def dispatch(
        self,
        task_id: int,
        task_type: Optional[TaskType] = None,
        resource_id: Optional[int] = None,
    ) -> bool:
        try:
            from infrastructure.tasks.tasks.task_executor import process_single_task

            # Send to Celery broker
            process_single_task.delay(task_id=task_id)

            logger.info(
                "task_dispatched",
                task_id=task_id,
                task_type=task_type.value if task_type else None,
            )
            return True

        except Exception as e:
            # Dispatch failure is non-fatal; task will be picked up by polling
            logger.error(
                "task_dispatch_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            return False


# Singleton instance
_dispatcher: Optional[CeleryTaskDispatcher] = None


def get_task_dispatcher() -> TaskDispatcherPort:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CeleryTaskDispatcher()
    return _dispatcher
```

### Use in Application Service

```python
# application/services/item_service.py
# Example: Replace "Item" with your domain entity (Document, Order, Report, etc.)

class ItemApplicationService:
    """Application service demonstrating task dispatch pattern.

    Customize:
        - Class name: DocumentService, OrderService, ReportService, etc.
        - Method name: upload_document, process_order, generate_report, etc.
        - TaskType: DOCUMENT_PARSE, ORDER_PROCESS, REPORT_GENERATE, etc.
    """

    def __init__(
        self,
        uow_factory: Callable,
        task_dispatcher: TaskDispatcherPort,
    ):
        self._uow_factory = uow_factory
        self._task_dispatcher = task_dispatcher

    async def process_item(self, resource_id: int, payload: bytes) -> TaskDTO:
        # 1. Create task record in database
        async with self._uow_factory() as uow:
            task = Task(resource_id=resource_id, type=TaskType.PROCESS_ITEM)
            created = await uow.task_repository.create(task)

        # 2. Dispatch to Celery (fire-and-forget)
        self._task_dispatcher.dispatch(
            task_id=created.id,
            task_type=TaskType.PROCESS_ITEM,
            resource_id=resource_id,
        )

        return TaskDTO.from_entity(created)
```

---

## Task Routing & Prioritization

### Dynamic Task Router

Route tasks to different processors based on configuration:

```python
# infrastructure/tasks/tasks/task_router.py
import asyncio
from celery import shared_task
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork
from ..utils.base_task import BaseTask

logger = get_logger(__name__)


# Define processor types as constants or Enum
class ProcessorType:
    """Processor types for task routing.

    Customize based on your domain:
        - SYNC / ASYNC
        - DOCUMENT / IMAGE / VIDEO
        - INTERNAL / EXTERNAL
        - HIGH_PRIORITY / LOW_PRIORITY
    """
    SYNC = "sync"
    ASYNC = "async"


async def _route_pending_tasks(max_tasks: int = 10) -> int:
    """Route pending tasks to appropriate processors."""
    from .sync_processor import process_sync_batch
    from .async_processor import process_async_batch

    processed = 0

    async with SQLAlchemyUnitOfWork() as uow:
        # Fetch pending tasks with row lock to prevent concurrent processing
        pending = await uow.task_repository.list(
            statuses=[TaskStatus.PENDING],
            limit=max_tasks,
            for_update=True,  # SELECT ... FOR UPDATE SKIP LOCKED
        )

        if not pending:
            return 0

        # Group tasks by processor type (customize grouping logic)
        sync_tasks = []
        async_tasks = []

        for task in pending:
            if task.processor_type == ProcessorType.SYNC:
                sync_tasks.append(task)
            else:
                async_tasks.append(task)

        # Mark all as RUNNING before processing
        for task in pending:
            task.mark_running()
            await uow.task_repository.update(task)

    # Process each group with appropriate processor
    if sync_tasks:
        processed += await process_sync_batch(sync_tasks)

    if async_tasks:
        processed += await process_async_batch(async_tasks)

    return processed


@shared_task(
    bind=True,
    base=BaseTask,
    name="infrastructure.tasks.tasks.task_router.route_pending_tasks",
    max_retries=3,
    default_retry_delay=60,
)
def route_pending_tasks(self, max_tasks: int = 10) -> int:
    try:
        return asyncio.run(_route_pending_tasks(max_tasks))
    except Exception as exc:
        logger.error("route_pending_tasks_failed", error=str(exc))
        raise self.retry(exc=exc)
```

### Priority Queue Usage

```python
# Send to high priority queue
process_urgent.apply_async(
    args=[item_id],
    queue="high",
)

# Send to low priority queue
process_batch.apply_async(
    args=[batch_data],
    queue="low",
)

# Default queue
process_normal.delay(item_id)
```

---

## Periodic Tasks (Beat)

### Beat Schedule Configuration

```python
# infrastructure/tasks/config/beat.py
from celery.schedules import crontab
from core.config import settings

CELERY_BEAT_SCHEDULE = {
    # Run every 10 seconds
    "route-pending-tasks": {
        "task": "infrastructure.tasks.tasks.task_router.route_pending_tasks",
        "schedule": settings.celery_beat.task_route_interval,  # e.g., 10.0
        "kwargs": {"max_tasks": settings.celery_beat.task_route_max_tasks},
    },

    # Run daily at midnight UTC
    "cleanup-expired-data": {
        "task": "infrastructure.tasks.tasks.maintenance.cleanup_expired",
        "schedule": crontab(hour=0, minute=0),
    },

    # Run every Monday at 3:00 AM
    "weekly-report": {
        "task": "infrastructure.tasks.tasks.reports.generate_weekly",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),
    },

    # Run every hour at minute 30
    "hourly-sync": {
        "task": "infrastructure.tasks.tasks.sync.sync_external",
        "schedule": crontab(minute=30),
    },
}
```

### Include Beat Schedule in Celery Config

```python
# infrastructure/tasks/config/celery.py
from .beat import CELERY_BEAT_SCHEDULE

celery_app.conf.update(
    beat_schedule=CELERY_BEAT_SCHEDULE,
    # ... other settings
)
```

### Running Beat

```bash
# Development
celery -A infrastructure.tasks.config.celery beat --loglevel=info

# Production (with worker)
celery -A infrastructure.tasks.config.celery worker --beat --loglevel=info

# Separate beat process (recommended for production)
celery -A infrastructure.tasks.config.celery beat --loglevel=info --pidfile=/var/run/celery/beat.pid
```

---

## Async Task Execution

### Running Async Code in Celery Tasks

Celery tasks are synchronous, but FastAPI apps are async. Bridge them properly:

```python
# infrastructure/tasks/tasks/task_executor.py
import asyncio
from celery import shared_task
from infrastructure.database import dispose_engine
from ..utils.base_task import BaseTask

logger = get_logger(__name__)


async def _process_task_async(task_id: int) -> bool:
    """Async implementation of task processing."""
    async with SQLAlchemyUnitOfWork() as uow:
        task = await uow.task_repository.get_by_id(task_id)

        if task is None:
            logger.warning("task_not_found", task_id=task_id)
            return False

        # Only process PENDING tasks (idempotency)
        if task.status != TaskStatus.PENDING:
            logger.debug("task_skipped_not_pending", task_id=task_id)
            return False

        # Mark as RUNNING
        task.mark_running()
        await uow.task_repository.update(task)

    try:
        # Execute actual work
        await do_async_work(task_id)

        # Mark as COMPLETED
        async with SQLAlchemyUnitOfWork() as uow:
            task = await uow.task_repository.get_by_id(task_id)
            task.mark_completed()
            await uow.task_repository.update(task)

        return True

    except Exception as e:
        # Mark as FAILED
        async with SQLAlchemyUnitOfWork() as uow:
            task = await uow.task_repository.get_by_id(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.mark_failed(error_message=str(e)[:500])
                await uow.task_repository.update(task)
        raise

    finally:
        # Clean up database connections
        await dispose_engine()


@shared_task(
    bind=True,
    base=BaseTask,
    name="infrastructure.tasks.tasks.task_executor.process_single_task",
)
def process_single_task(self, task_id: int) -> bool:
    """Celery task wrapper for async processing."""
    try:
        return asyncio.run(_process_task_async(task_id))
    except Exception as exc:
        logger.error("process_single_task_failed", task_id=task_id, error=str(exc))
        # Don't retry - task state is already updated
        return False
```

### Database Connection Cleanup

Always dispose of database connections after async operations:

```python
# infrastructure/database.py
async def dispose_engine():
    """Dispose async engine to clean up connections."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
```

---

## Error Handling & Retry

### Retry Strategies

```python
# Automatic retry for specific exceptions
@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, TransientAPIError),
    retry_backoff=True,         # Exponential: 1s, 2s, 4s, 8s...
    retry_backoff_max=600,      # Cap at 10 minutes
    retry_jitter=True,          # Add randomness
    max_retries=5,
)
def resilient_task(self, data):
    return call_external_api(data)


# Manual retry with custom logic
@shared_task(bind=True, max_retries=3)
def custom_retry_task(self, item_id):
    try:
        return process(item_id)
    except RateLimitError as exc:
        # Retry after rate limit resets
        retry_after = exc.retry_after or 60
        raise self.retry(exc=exc, countdown=retry_after)
    except PermanentError:
        # Don't retry permanent failures
        raise
```

### Exception Classification

```python
# Define which exceptions are transient vs permanent
class TransientError(Exception):
    """Temporary failure, safe to retry."""
    pass

class PermanentError(Exception):
    """Permanent failure, don't retry."""
    pass

class RateLimitError(TransientError):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after
```

---

## Idempotency & State Management

### Task State Machine

```python
# domain/task/entity.py
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    def mark_running(self):
        if self.status != TaskStatus.PENDING:
            raise InvalidStateTransition(f"Cannot start task in {self.status} state")
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self):
        if self.status != TaskStatus.RUNNING:
            raise InvalidStateTransition(f"Cannot complete task in {self.status} state")
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error_message: str):
        self.status = TaskStatus.FAILED
        self.error_message = error_message[:500]  # Truncate
        self.completed_at = datetime.utcnow()
```

### Idempotent Processing

```python
async def process_task(task_id: int) -> bool:
    async with SQLAlchemyUnitOfWork() as uow:
        task = await uow.task_repository.get_by_id(task_id)

        # Idempotency check: only process PENDING
        if task.status != TaskStatus.PENDING:
            logger.debug(
                "task_already_processed",
                task_id=task_id,
                status=task.status,
            )
            return False

        # Use FOR UPDATE to prevent concurrent processing
        task = await uow.task_repository.get_by_id(task_id, for_update=True)

        # Double-check after lock
        if task.status != TaskStatus.PENDING:
            return False

        task.mark_running()
        await uow.task_repository.update(task)

    # Process outside transaction
    await do_work(task)

    return True
```

---

## Testing Celery Tasks

### Unit Testing Tasks

```python
# tests/tasks/test_processor.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_process_task_success():
    """Test successful task processing."""
    with patch("infrastructure.tasks.tasks.processor.SQLAlchemyUnitOfWork") as mock_uow:
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = Task(
            id=1,
            status=TaskStatus.PENDING,
        )
        mock_uow.return_value.__aenter__.return_value.task_repository = mock_repo

        result = await _process_task_async(task_id=1)

        assert result is True
        mock_repo.update.assert_called()


@pytest.mark.asyncio
async def test_process_task_skips_non_pending():
    """Test that non-pending tasks are skipped."""
    with patch("infrastructure.tasks.tasks.processor.SQLAlchemyUnitOfWork") as mock_uow:
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = Task(
            id=1,
            status=TaskStatus.RUNNING,  # Already running
        )
        mock_uow.return_value.__aenter__.return_value.task_repository = mock_repo

        result = await _process_task_async(task_id=1)

        assert result is False
```

### Integration Testing with Eager Mode

```python
# tests/conftest.py
import pytest
from infrastructure.tasks.config.celery import celery_app


@pytest.fixture(autouse=True)
def celery_eager_mode():
    """Run Celery tasks synchronously in tests."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


def test_dispatch_and_process(celery_eager_mode, db_session):
    """Test full dispatch-to-process flow."""
    # Create task
    task = create_test_task(db_session)

    # Dispatch (runs synchronously due to eager mode)
    from infrastructure.tasks.tasks.task_executor import process_single_task
    result = process_single_task.delay(task_id=task.id)

    # Verify result
    assert result.get() is True

    # Verify task state
    db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
```

---

## Monitoring & Observability

### Structured Logging

```python
from core.logging_config import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, base=BaseTask)
def monitored_task(self, item_id: int):
    logger.info(
        "task_started",
        celery_task_id=self.request.id,
        item_id=item_id,
    )

    try:
        result = process(item_id)
        logger.info(
            "task_completed",
            celery_task_id=self.request.id,
            item_id=item_id,
            result_size=len(result),
        )
        return result

    except Exception as e:
        logger.error(
            "task_failed",
            celery_task_id=self.request.id,
            item_id=item_id,
            error=str(e),
            exc_info=True,
        )
        raise
```

### Sentry Integration

```python
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[CeleryIntegration()],
    traces_sample_rate=0.1,
)
```

### Flower Monitoring

```bash
# Install
pip install flower

# Run
celery -A infrastructure.tasks.config.celery flower --port=5555

# With basic auth
celery -A infrastructure.tasks.config.celery flower \
    --basic_auth=admin:password \
    --port=5555
```

---

## Common Pitfalls

### 1. Blocking the Event Loop

```python
# ❌ WRONG: Calling async from sync without asyncio.run
@shared_task
def bad_task(item_id):
    await async_process(item_id)  # SyntaxError or RuntimeError

# ✅ CORRECT: Use asyncio.run
@shared_task
def good_task(item_id):
    return asyncio.run(async_process(item_id))
```

### 2. Database Connection Leaks

```python
# ❌ WRONG: Not disposing connections
@shared_task
def leaky_task(item_id):
    asyncio.run(process_with_db(item_id))
    # Connections left open!

# ✅ CORRECT: Always dispose
@shared_task
def clean_task(item_id):
    try:
        return asyncio.run(process_with_db(item_id))
    finally:
        asyncio.run(dispose_engine())
```

### 3. Non-JSON Serializable Arguments

```python
# ❌ WRONG: Passing complex objects
my_task.delay(user=User(...))  # TypeError

# ✅ CORRECT: Pass IDs or primitive types
my_task.delay(user_id=user.id)
```

### 4. Missing Idempotency

```python
# ❌ WRONG: Task can run multiple times with side effects
@shared_task(autoretry_for=(Exception,))
def non_idempotent_task(amount):
    add_to_balance(amount)  # Runs multiple times on retry!

# ✅ CORRECT: Check if already processed
@shared_task(autoretry_for=(Exception,))
def idempotent_task(transaction_id, amount):
    if is_processed(transaction_id):
        return
    add_to_balance(amount)
    mark_processed(transaction_id)
```

### 5. Retry Without Backoff

```python
# ❌ WRONG: Fixed retry delay causes thundering herd
@shared_task(max_retries=10, default_retry_delay=5)
def hammering_task(item_id):
    raise self.retry()

# ✅ CORRECT: Exponential backoff with jitter
@shared_task(
    max_retries=10,
    retry_backoff=True,
    retry_jitter=True,
)
def polite_task(item_id):
    raise self.retry()
```

### 6. Long-Running Tasks Without Timeout

```python
# ❌ WRONG: Task can run forever
@shared_task
def infinite_task(data):
    while True:
        process_chunk(data)

# ✅ CORRECT: Set time limits
@shared_task(soft_time_limit=300, time_limit=360)
def bounded_task(data):
    for chunk in data:
        process_chunk(chunk)
```

---

## Quick Reference

### Worker Commands

```bash
# Start worker
celery -A infrastructure.tasks.config.celery worker --loglevel=info

# Start worker with specific queues
celery -A infrastructure.tasks.config.celery worker -Q high,default --loglevel=info

# Start worker with concurrency
celery -A infrastructure.tasks.config.celery worker --concurrency=4

# Start beat scheduler
celery -A infrastructure.tasks.config.celery beat --loglevel=info

# Start worker + beat (development only)
celery -A infrastructure.tasks.config.celery worker --beat --loglevel=info
```

### Task Invocation

```python
# Async dispatch (returns AsyncResult)
result = my_task.delay(arg1, arg2)
result = my_task.apply_async(args=[arg1], kwargs={"key": "value"})

# With options
my_task.apply_async(
    args=[item_id],
    queue="high",
    countdown=10,          # Delay execution by 10 seconds
    expires=3600,          # Expire after 1 hour
    retry=False,           # Disable automatic retry
)

# Get result (blocks)
value = result.get(timeout=30)

# Check status
result.ready()    # True if completed
result.successful()  # True if succeeded
result.failed()   # True if failed
result.state      # PENDING, STARTED, SUCCESS, FAILURE, etc.
```

### Configuration Checklist

- [ ] `task_acks_late=True` for reliability
- [ ] `task_reject_on_worker_lost=True` for fault tolerance
- [ ] `task_serializer="json"` for security
- [ ] `result_expires` set to avoid backend bloat
- [ ] `worker_prefetch_multiplier=1` for fair distribution
- [ ] Priority queues defined for different workloads
- [ ] Time limits set for long-running tasks
- [ ] Retry strategy with exponential backoff
- [ ] Structured logging in all tasks
- [ ] Sentry integration for error tracking

---

## Customization Guide

This document uses **generic placeholders**. Replace them with your domain-specific terms:

### Naming Conventions

| Placeholder | Example Replacements |
|-------------|---------------------|
| `resource_id` | `document_id`, `order_id`, `report_id`, `user_id` |
| `TaskType.PROCESS_ITEM` | `TaskType.PARSE_DOCUMENT`, `TaskType.PROCESS_ORDER` |
| `ItemApplicationService` | `DocumentService`, `OrderService`, `ReportService` |
| `process_item()` | `upload_document()`, `submit_order()`, `generate_report()` |
| `ProcessorType.SYNC/ASYNC` | `ProcessorType.PDF/IMAGE`, `ProcessorType.INTERNAL/EXTERNAL` |

### Common Domain Patterns

```python
# Document Processing Domain
class TaskType(str, Enum):
    PARSE_PDF = "parse_pdf"
    EXTRACT_TEXT = "extract_text"
    GENERATE_SUMMARY = "generate_summary"

# E-commerce Domain
class TaskType(str, Enum):
    PROCESS_ORDER = "process_order"
    SEND_NOTIFICATION = "send_notification"
    GENERATE_INVOICE = "generate_invoice"

# Data Pipeline Domain
class TaskType(str, Enum):
    ETL_EXTRACT = "etl_extract"
    ETL_TRANSFORM = "etl_transform"
    ETL_LOAD = "etl_load"
```

### Adding Domain-Specific Parameters

```python
# Extend the base dispatch interface for your domain
class TaskDispatcherPort(ABC):
    @abstractmethod
    def dispatch(
        self,
        task_id: int,
        task_type: Optional[TaskType] = None,
        # Add your domain-specific parameters:
        document_id: Optional[int] = None,      # Document domain
        priority: Optional[str] = None,          # Priority routing
        metadata: Optional[dict] = None,         # Flexible context
        callback_url: Optional[str] = None,      # Webhook integration
    ) -> bool:
        ...
```

