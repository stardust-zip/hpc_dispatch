from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func

from .. import models, schemas, utils
from ..auth import get_current_user, get_current_lecturer
from ..database import get_session

router = APIRouter(
    prefix="/dispatches",
    tags=["Dispatches"],
)


@router.post(
    "", response_model=schemas.DispatchRead, status_code=status.HTTP_201_CREATED
)
def create_dispatch(
    *,
    session: Session = Depends(get_session),
    dispatch_data: schemas.DispatchCreate,
    current_user: models.User = Depends(get_current_lecturer),
):
    if not dispatch_data.assignee_ids:
        raise HTTPException(
            status_code=400, detail="At least one assignee ID is required."
        )

    dispatch = models.Dispatch(
        title=dispatch_data.title,
        content=dispatch_data.content,
        creator_id=current_user.id,
    )

    for assignee_id in set(dispatch_data.assignee_ids):
        dispatch.assignee_links.append(
            models.DispatchAssigneeLink(assignee_id=assignee_id)
        )

    for file_url in dispatch_data.files:
        dispatch.files.append(
            models.DispatchFile(file_url=file_url, filename=file_url.split("/")[-1])
        )

    dispatch.history.append(
        models.DispatchHistory(
            actor_id=current_user.id, action=models.DispatchAction.CREATED
        )
    )
    session.add(dispatch)
    session.commit()
    session.refresh(dispatch)
    return utils.convert_dispatch_to_read_model(dispatch)


@router.get("", response_model=schemas.PaginatedResponse[schemas.DispatchRead])
def get_my_dispatches(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user),
    status: Optional[models.DispatchStatus] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    shelf_id: Optional[int] = Query(None, description="Filter dispatches by shelf ID"),
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(
        "created_at", enum=["created_at", "title", "status"]
    ),
    sort_dir: Optional[str] = Query("desc", enum=["asc", "desc"]),
):
    statement = select(models.Dispatch)

    if shelf_id:
        shelf = session.get(models.Shelf, shelf_id)
        if not shelf or shelf.user_id != current_user.id:
            raise HTTPException(
                status_code=404, detail="Shelf not found or not authorized"
            )
        statement = statement.join(models.DispatchShelfLink).where(
            models.DispatchShelfLink.shelf_id == shelf_id
        )

    if direction == "incoming":
        statement = statement.join(models.DispatchAssigneeLink).where(
            models.DispatchAssigneeLink.assignee_id == current_user.id
        )
    elif direction == "outgoing":
        statement = statement.where(models.Dispatch.creator_id == current_user.id)
    elif not shelf_id:
        is_assignee_query = (
            select(models.Dispatch.id)
            .join(models.DispatchAssigneeLink)
            .where(models.DispatchAssigneeLink.assignee_id == current_user.id)
        )
        statement = statement.where(
            (models.Dispatch.creator_id == current_user.id)
            | (models.Dispatch.id.in_(is_assignee_query))
        )

    if status:
        statement = statement.where(models.Dispatch.status == status)
    if search:
        statement = statement.where(
            (models.Dispatch.title.contains(search))
            | (models.Dispatch.content.contains(search))
        )

    sort_column = getattr(models.Dispatch, sort_by, models.Dispatch.created_at)
    statement = statement.order_by(
        sort_column.desc() if sort_dir == "desc" else sort_column.asc()
    )

    count_statement = select(func.count()).select_from(statement.subquery())
    total_count = session.exec(count_statement).one()
    dispatches = session.exec(statement.offset(skip).limit(limit)).all()

    items = [utils.convert_dispatch_to_read_model(d) for d in dispatches]
    return schemas.PaginatedResponse(total=total_count, items=items)


@router.get("/{dispatch_id}", response_model=schemas.DispatchReadWithDetails)
def get_dispatch_details(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    current_user: models.User = Depends(get_current_user),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    assignee_ids = [link.assignee_id for link in dispatch.assignee_links]
    if not current_user.is_admin and (
        dispatch.creator_id != current_user.id and current_user.id not in assignee_ids
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this dispatch"
        )

    return utils.convert_dispatch_to_detailed_read_model(dispatch)


@router.put("/{dispatch_id}", response_model=schemas.DispatchRead)
def update_dispatch(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    dispatch_data: schemas.DispatchUpdate,
    current_user: models.User = Depends(get_current_lecturer),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    is_admin = current_user.is_admin
    is_creator = dispatch.creator_id == current_user.id
    is_draft = dispatch.status == models.DispatchStatus.DRAFT

    if not (is_admin or (is_creator and is_draft)):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this dispatch"
        )

    update_data = dispatch_data.model_dump(exclude_unset=True)
    if "assignee_ids" in update_data:
        if not is_draft and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Assignees can only be changed on DRAFT dispatches.",
            )
        dispatch.assignee_links = [
            models.DispatchAssigneeLink(assignee_id=id)
            for id in set(update_data["assignee_ids"])
        ]

    if "title" in update_data:
        dispatch.title = update_data["title"]
    if "content" in update_data:
        dispatch.content = update_data["content"]

    dispatch.history.append(
        models.DispatchHistory(
            actor_id=current_user.id, action=models.DispatchAction.MODIFIED
        )
    )
    session.add(dispatch)
    session.commit()
    session.refresh(dispatch)
    return utils.convert_dispatch_to_read_model(dispatch)


@router.post("/{dispatch_id}/send", response_model=schemas.DispatchRead)
def send_dispatch(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    current_user: models.User = Depends(get_current_lecturer),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    if dispatch.creator_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the creator can send this dispatch"
        )
    if dispatch.status != models.DispatchStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Dispatch is not in draft state")

    dispatch.status = models.DispatchStatus.PENDING
    dispatch.history.append(
        models.DispatchHistory(
            actor_id=current_user.id, action=models.DispatchAction.SENT
        )
    )
    session.add(dispatch)
    session.commit()
    session.refresh(dispatch)
    return utils.convert_dispatch_to_read_model(dispatch)


@router.put("/{dispatch_id}/status", response_model=schemas.DispatchRead)
def update_dispatch_status(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    status_update: schemas.DispatchStatusUpdate,
    current_user: models.User = Depends(get_current_lecturer),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    assignee_ids = [link.assignee_id for link in dispatch.assignee_links]
    if not current_user.is_admin and current_user.id not in assignee_ids:
        raise HTTPException(
            status_code=403, detail="Only an assignee or admin can update the status"
        )

    dispatch.status = status_update.status
    dispatch.history.append(
        models.DispatchHistory(
            actor_id=current_user.id,
            action=models.DispatchAction.STATUS_UPDATED,
            details=f"Status changed to {status_update.status.value}",
        )
    )
    session.add(dispatch)
    session.commit()
    session.refresh(dispatch)
    return utils.convert_dispatch_to_read_model(dispatch)


@router.post("/{dispatch_id}/comments", response_model=models.Comment)
def add_comment_to_dispatch(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    comment_data: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    assignee_ids = [link.assignee_id for link in dispatch.assignee_links]
    if not current_user.is_admin and (
        dispatch.creator_id != current_user.id and current_user.id not in assignee_ids
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to comment on this dispatch"
        )

    comment = models.Comment.model_validate(
        comment_data, update={"user_id": current_user.id, "dispatch_id": dispatch_id}
    )
    dispatch.history.append(
        models.DispatchHistory(
            actor_id=current_user.id, action=models.DispatchAction.COMMENTED
        )
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.delete("/{dispatch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dispatch(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    current_user: models.User = Depends(get_current_lecturer),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if dispatch:
        is_admin = current_user.is_admin
        is_creator = dispatch.creator_id == current_user.id
        is_draft = dispatch.status == models.DispatchStatus.DRAFT
        if is_admin or (is_creator and is_draft):
            session.delete(dispatch)
            session.commit()
        else:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this dispatch"
            )
    return


@router.post("/{dispatch_id}/forward", response_model=schemas.DispatchRead)
def forward_dispatch(
    *,
    session: Session = Depends(get_session),
    dispatch_id: int,
    forward_data: schemas.DispatchForward,
    current_user: models.User = Depends(get_current_lecturer),
):
    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    assignee_ids = [link.assignee_id for link in dispatch.assignee_links]
    if not current_user.is_admin and current_user.id not in assignee_ids:
        raise HTTPException(
            status_code=403, detail="Only a current assignee or admin can forward"
        )
    if dispatch.status in [
        models.DispatchStatus.DRAFT,
        models.DispatchStatus.COMPLETED,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot forward a dispatch with status '{dispatch.status}'",
        )

    new_assignee_id = forward_data.new_assignee_id
    if new_assignee_id in assignee_ids:
        return utils.convert_dispatch_to_read_model(dispatch)

    dispatch.assignee_links.append(
        models.DispatchAssigneeLink(assignee_id=new_assignee_id)
    )
    dispatch.history.append(
        models.DispatchHistory(
            actor_id=current_user.id,
            action=models.DispatchAction.FORWARDED,
            details=f"Forwarded to user {new_assignee_id}",
        )
    )
    session.add(dispatch)
    session.commit()
    session.refresh(dispatch)
    return utils.convert_dispatch_to_read_model(dispatch)
