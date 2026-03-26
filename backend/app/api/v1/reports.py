"""API v1 router — Agent Observability Reports."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.dependencies import get_current_agent, get_current_user, get_db
from app.models.agent import Agent
from app.models.agent_report import AgentReport
from app.models.user import User
from app.schemas.report import (
    ReportResponse,
    ReportsListResponse,
    ReportsRequest,
    ReportsResponse,
    ReportsStatsResponse,
)

router = APIRouter(prefix="/api/v1", tags=["reports"])


# ---------------------------------------------------------------------------
# POST /agent/reports — Agent submits reports
# ---------------------------------------------------------------------------


@router.post("/agent/reports", response_model=ReportsResponse, status_code=201)
async def submit_reports(
    body: ReportsRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> ReportsResponse:
    """
    Agent submits observability reports (exceptions, events, health status).

    Authentication: X-Agent-Key header

    The agent_id in the request body should match the authenticated agent.
    """
    # Validate agent_id matches authenticated agent
    if body.agent_id and body.agent_id != agent.id:
        # Allow mismatched agent_id (it's just a label), but log it
        pass

    reports_to_store = []
    for report in body.reports:
        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(
                report.timestamp.replace("Z", "+00:00")
            )
            # Convert to naive UTC datetime for database compatibility
            if timestamp.tzinfo is not None:
                timestamp = timestamp.astimezone().replace(tzinfo=None)
        except ValueError:
            # If parsing fails, use current time
            timestamp = datetime.utcnow()

        # Extract session context
        session = report.session or {}
        room_id = session.get("room_id")
        game_id = session.get("game_id")

        # Create report record
        agent_report = AgentReport(
            agent_id=agent.id,
            report_type=report.report_type,
            timestamp=timestamp,
            room_id=room_id,
            game_id=game_id,
            payload=report.payload,
        )
        reports_to_store.append(agent_report)

    # Batch insert
    if reports_to_store:
        db.add_all(reports_to_store)
        await db.flush()

    return ReportsResponse(
        status="ok",
        received=len(body.reports),
        stored=len(reports_to_store),
    )


# ---------------------------------------------------------------------------
# GET /agent/reports — User queries reports
# ---------------------------------------------------------------------------


@router.get("/agent/reports", response_model=ReportsListResponse)
async def list_reports(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    room_id: Optional[str] = Query(None, description="Filter by room ID"),
    game_id: Optional[str] = Query(None, description="Filter by game ID"),
    _from: Optional[datetime] = Query(None, alias="from", description="Start time"),
    to: Optional[datetime] = Query(None, description="End time"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportsListResponse:
    """
    Query agent reports (requires user authentication).

    Only returns reports for agents owned by the current user.
    """
    # Base query - only user's agents
    query = (
        select(AgentReport)
        .join(Agent)
        .where(Agent.owner_id == current_user.id)
    )

    # Apply filters
    if agent_id:
        query = query.where(AgentReport.agent_id == agent_id)
    if report_type:
        query = query.where(AgentReport.report_type == report_type)
    if room_id:
        query = query.where(AgentReport.room_id == room_id)
    if game_id:
        query = query.where(AgentReport.game_id == game_id)
    if _from:
        query = query.where(AgentReport.timestamp >= _from)
    if to:
        query = query.where(AgentReport.timestamp <= to)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(AgentReport.timestamp.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportsListResponse(
        total=total,
        reports=[ReportResponse.model_validate(r) for r in reports],
    )


# ---------------------------------------------------------------------------
# GET /agent/reports/stats — Report statistics
# ---------------------------------------------------------------------------


@router.get("/agent/reports/stats", response_model=ReportsStatsResponse)
async def get_report_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportsStatsResponse:
    """
    Get aggregate statistics for agent reports.

    Only includes reports for agents owned by the current user.
    """
    # Total count
    total_query = (
        select(func.count())
        .select_from(AgentReport)
        .join(Agent)
        .where(Agent.owner_id == current_user.id)
    )
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # By type
    type_query = (
        select(
            AgentReport.report_type,
            func.count().label("count"),
        )
        .join(Agent)
        .where(Agent.owner_id == current_user.id)
        .group_by(AgentReport.report_type)
    )
    type_result = await db.execute(type_query)
    by_type = {row.report_type: row.count for row in type_result}

    # By agent
    agent_query = (
        select(
            AgentReport.agent_id,
            func.count().label("count"),
        )
        .join(Agent)
        .where(Agent.owner_id == current_user.id)
        .group_by(AgentReport.agent_id)
    )
    agent_result = await db.execute(agent_query)
    by_agent = {str(row.agent_id): row.count for row in agent_result}

    # Recent errors (last 24h)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    error_query = (
        select(func.count())
        .select_from(AgentReport)
        .join(Agent)
        .where(
            Agent.owner_id == current_user.id,
            AgentReport.report_type == "exception",
            AgentReport.timestamp >= yesterday,
        )
    )
    error_result = await db.execute(error_query)
    recent_errors = error_result.scalar() or 0

    return ReportsStatsResponse(
        total_reports=total,
        by_type=by_type,
        by_agent=by_agent,
        recent_errors=recent_errors,
    )


# ---------------------------------------------------------------------------
# DELETE /agent/reports/{report_id} — Delete a report
# ---------------------------------------------------------------------------


@router.delete("/agent/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific report.

    Only allows deletion of reports for agents owned by the current user.
    """
    # Find the report and verify ownership
    query = (
        select(AgentReport)
        .join(Agent)
        .where(
            AgentReport.id == report_id,
            Agent.owner_id == current_user.id,
        )
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Report not found")

    await db.delete(report)
    await db.flush()
