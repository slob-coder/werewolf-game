"""API v1 router — Server Exception management."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_current_user, get_db
from app.models.server_exception import ServerException
from app.models.user import User
from app.schemas.server_exception import (
    ExceptionListResponse,
    ExceptionResponse,
    ExceptionStatsResponse,
    ResolveExceptionRequest,
    ResolveExceptionResponse,
)

router = APIRouter(prefix="/api/v1/server-exceptions", tags=["server-exceptions"])


# ---------------------------------------------------------------------------
# GET /server-exceptions — List exceptions
# ---------------------------------------------------------------------------


@router.get("", response_model=ExceptionListResponse)
async def list_exceptions(
    exception_type: Optional[str] = Query(None, description="Filter by exception type"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    room_id: Optional[str] = Query(None, description="Filter by room ID"),
    game_id: Optional[str] = Query(None, description="Filter by game ID"),
    _from: Optional[datetime] = Query(None, alias="from", description="Start time"),
    to: Optional[datetime] = Query(None, description="End time"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExceptionListResponse:
    """
    Query server exceptions (requires authentication).

    Useful for debugging and monitoring server-side errors.
    """
    # Base query
    query = select(ServerException)

    # Apply filters
    if exception_type:
        query = query.where(ServerException.exception_type == exception_type)
    if resolved is not None:
        query = query.where(ServerException.resolved == resolved)
    if room_id:
        query = query.where(ServerException.room_id == room_id)
    if game_id:
        query = query.where(ServerException.game_id == game_id)
    if _from:
        query = query.where(ServerException.created_at >= _from)
    if to:
        query = query.where(ServerException.created_at <= to)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(ServerException.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    exceptions = result.scalars().all()

    return ExceptionListResponse(
        total=total,
        exceptions=[ExceptionResponse.model_validate(e) for e in exceptions],
    )


# ---------------------------------------------------------------------------
# GET /server-exceptions/stats — Exception statistics
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=ExceptionStatsResponse)
async def get_exception_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExceptionStatsResponse:
    """
    Get aggregate statistics for server exceptions.
    """
    # Total count
    total_query = select(func.count()).select_from(ServerException)
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # By type
    type_query = select(
        ServerException.exception_type,
        func.count().label("count"),
    ).group_by(ServerException.exception_type)
    type_result = await db.execute(type_query)
    by_type = {row.exception_type: row.count for row in type_result}

    # Unresolved count
    unresolved_query = select(func.count()).select_from(ServerException).where(
        ServerException.resolved == False
    )
    unresolved_result = await db.execute(unresolved_query)
    unresolved = unresolved_result.scalar() or 0

    # Recent exceptions (last 24h)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_query = select(func.count()).select_from(ServerException).where(
        ServerException.created_at >= yesterday
    )
    recent_result = await db.execute(recent_query)
    recent = recent_result.scalar() or 0

    return ExceptionStatsResponse(
        total_exceptions=total,
        by_type=by_type,
        unresolved=unresolved,
        recent_exceptions=recent,
    )


# ---------------------------------------------------------------------------
# GET /server-exceptions/{exception_id} — Get single exception
# ---------------------------------------------------------------------------


@router.get("/{exception_id}", response_model=ExceptionResponse)
async def get_exception(
    exception_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExceptionResponse:
    """
    Get details of a specific exception.
    """
    query = select(ServerException).where(ServerException.id == exception_id)
    result = await db.execute(query)
    exception = result.scalar_one_or_none()

    if exception is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Exception not found")

    return ExceptionResponse.model_validate(exception)


# ---------------------------------------------------------------------------
# PATCH /server-exceptions/{exception_id}/resolve — Mark exception as resolved
# ---------------------------------------------------------------------------


@router.patch(
    "/{exception_id}/resolve",
    response_model=ResolveExceptionResponse,
)
async def resolve_exception(
    exception_id: str,
    body: ResolveExceptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResolveExceptionResponse:
    """
    Mark an exception as resolved with a note.
    """
    query = select(ServerException).where(ServerException.id == exception_id)
    result = await db.execute(query)
    exception = result.scalar_one_or_none()

    if exception is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Exception not found")

    # Update exception
    exception.resolved = True
    exception.resolved_at = datetime.utcnow()
    exception.resolved_by = current_user.email or str(current_user.id)
    exception.resolution_note = body.note

    await db.commit()
    await db.refresh(exception)

    return ResolveExceptionResponse(
        status="ok",
        exception=ExceptionResponse.model_validate(exception),
    )


# ---------------------------------------------------------------------------
# DELETE /server-exceptions/{exception_id} — Delete exception
# ---------------------------------------------------------------------------


@router.delete("/{exception_id}", status_code=204)
async def delete_exception(
    exception_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific exception record.
    """
    query = select(ServerException).where(ServerException.id == exception_id)
    result = await db.execute(query)
    exception = result.scalar_one_or_none()

    if exception is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Exception not found")

    await db.delete(exception)
    await db.commit()


# ---------------------------------------------------------------------------
# DELETE /server-exceptions — Bulk delete resolved exceptions
# ---------------------------------------------------------------------------


@router.delete("")
async def bulk_delete_resolved(
    older_than_days: int = Query(30, ge=1, description="Delete exceptions older than N days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Bulk delete resolved exceptions older than specified days.

    Default: delete resolved exceptions older than 30 days.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

    query = (
        select(ServerException)
        .where(
            ServerException.resolved == True,
            ServerException.created_at < cutoff_date,
        )
    )
    result = await db.execute(query)
    exceptions = result.scalars().all()

    count = len(exceptions)
    for exc in exceptions:
        await db.delete(exc)

    await db.commit()

    return {
        "status": "ok",
        "deleted": count,
    }
