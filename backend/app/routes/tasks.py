"""
Async task status polling route.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import AsyncTask, User
from app.schemas import TaskStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tasks"])


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Check the status of an async task",
)
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll the status of a background Celery task.

    Args:
        task_id: The task's primary key (not the Celery task ID).
        user: The authenticated user (injected).
        db: Database session (injected).

    Returns:
        Current task status, type, and result (if complete).

    Raises:
        HTTPException 404: If the task does not exist or belongs to
            another user.
    """
    result = await db.execute(
        select(AsyncTask).where(
            AsyncTask.id == task_id,
            AsyncTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskStatusResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        result=task.result,
        created_at=task.created_at,
    )
