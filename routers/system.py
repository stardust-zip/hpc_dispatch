from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func

from .. import models, schemas, utils
from ..auth import get_current_user, get_current_admin, MOCK_USERS
from ..config import settings
from ..database import get_session

router = APIRouter()


@router.get("/", tags=["System"], include_in_schema=False)
def root():
    return {"service": "HPC Dispatch Microservice", "version": "1.2.0", "status": "ok"}


@router.get("/plug", tags=["System"])
def get_plug_status():
    is_on = settings.MOCK_AUTH_ENABLED
    return {
        "plug_name": "mock_authentication",
        "status": "on" if is_on else "off",
        "description": "When 'on', auth uses mock users. Restart with MOCK_AUTH_ENABLED=true/false to change.",
        "available_mock_tokens": list(MOCK_USERS.keys()) if is_on else None,
    }


@router.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}


@router.get("/dispatches/stats/my", response_model=schemas.MyStats, tags=["Statistics"])
def get_my_stats(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    user_id = current_user.id
    incoming_count = session.exec(
        select(func.count(models.DispatchAssigneeLink.dispatch_id)).where(
            models.DispatchAssigneeLink.assignee_id == user_id
        )
    ).one()
    outgoing_count = session.exec(
        select(func.count(models.Dispatch.id)).where(
            models.Dispatch.creator_id == user_id
        )
    ).one()

    is_assignee_q = (
        select(models.Dispatch.id)
        .join(models.DispatchAssigneeLink)
        .where(models.DispatchAssigneeLink.assignee_id == user_id)
    )
    status_q = session.exec(
        select(models.Dispatch.status, func.count(models.Dispatch.id))
        .where(
            (models.Dispatch.creator_id == user_id)
            | (models.Dispatch.id.in_(is_assignee_q))
        )
        .group_by(models.Dispatch.status)
    ).all()

    status_counts = {s.value: 0 for s in models.DispatchStatus}
    status_counts.update({status: count for status, count in status_q})

    return schemas.MyStats(
        incoming=incoming_count, outgoing=outgoing_count, status_counts=status_counts
    )


@router.get(
    "/dispatches/stats/system", response_model=schemas.SystemStats, tags=["Statistics"]
)
def get_system_stats(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_admin),
    limit: int = 5
):
    total_dispatches = session.exec(select(func.count(models.Dispatch.id))).one()
    status_q = session.exec(
        select(models.Dispatch.status, func.count()).group_by(models.Dispatch.status)
    ).all()
    status_counts = {s.value: 0 for s in models.DispatchStatus}
    status_counts.update({status: count for status, count in status_q})

    creator_q = session.exec(
        select(models.Dispatch.creator_id, func.count().label("count"))
        .group_by(models.Dispatch.creator_id)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    top_creators = [
        schemas.UserActivityStat(user_id=uid, count=c) for uid, c in creator_q
    ]

    assignee_q = session.exec(
        select(models.DispatchAssigneeLink.assignee_id, func.count().label("count"))
        .group_by(models.DispatchAssigneeLink.assignee_id)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    top_assignees = [
        schemas.UserActivityStat(user_id=uid, count=c) for uid, c in assignee_q
    ]

    return schemas.SystemStats(
        total_dispatches=total_dispatches,
        status_counts=status_counts,
        top_creators=top_creators,
        top_assignees=top_assignees,
    )


@router.get(
    "/admin/dispatches",
    response_model=schemas.PaginatedResponse[schemas.DispatchRead],
    tags=["Admin"],
)
def get_all_dispatches(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_admin),
    assignee_id: Optional[int] = Query(None),
    creator_id: Optional[int] = Query(None),
    status: Optional[models.DispatchStatus] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    statement = select(models.Dispatch)
    if assignee_id:
        statement = statement.join(models.DispatchAssigneeLink).where(
            models.DispatchAssigneeLink.assignee_id == assignee_id
        )
    if creator_id:
        statement = statement.where(models.Dispatch.creator_id == creator_id)
    if status:
        statement = statement.where(models.Dispatch.status == status)
    if search:
        statement = statement.where(
            (models.Dispatch.title.contains(search))
            | (models.Dispatch.content.contains(search))
        )

    count_statement = select(func.count()).select_from(statement.subquery())
    total_count = session.exec(count_statement).one()
    dispatches = session.exec(
        statement.order_by(models.Dispatch.created_at.desc()).offset(skip).limit(limit)
    ).all()

    items = [utils.convert_dispatch_to_read_model(d) for d in dispatches]
    return schemas.PaginatedResponse(total=total_count, items=items)
