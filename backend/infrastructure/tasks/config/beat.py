"""Celery beat schedule configuration (optional).

Create entries here when you need periodic jobs; keeping the structure close
to the Celery docs makes copying snippets straightforward for new tasks.
"""

from __future__ import annotations

from typing import Any

CELERY_BEAT_SCHEDULE: dict[str, dict[str, Any]] = {
    # Example scheduled task definition
    # "sample-health-check": {
    #     "task": "infrastructure.tasks.tasks.email.send_welcome_email",
    #     "schedule": 3600,  # every hour
    #     "args": [0, "healthcheck@example.com"],
    # },
}
