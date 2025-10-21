from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_session

router = APIRouter(
    prefix="/shelves",
    tags=["Shelves"],
)


@router.post("", response_model=schemas.ShelfRead, status_code=status.HTTP_201_CREATED)
def create_shelf(
    *,
    session: Session = Depends(get_session),
    shelf_data: schemas.ShelfCreate,
    current_user: models.User = Depends(get_current_user)
):
    if shelf_data.parent_id:
        parent_shelf = session.get(models.Shelf, shelf_data.parent_id)
        if not parent_shelf:
            raise HTTPException(status_code=404, detail="Parent shelf not found")
        if parent_shelf.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Cannot create a shelf under another user's shelf",
            )

    db_shelf = models.Shelf.model_validate(
        shelf_data, update={"user_id": current_user.id}
    )
    session.add(db_shelf)
    session.commit()
    session.refresh(db_shelf)
    return db_shelf


@router.get("", response_model=List[schemas.ShelfReadWithChildren])
def get_my_top_level_shelves(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    shelves = (
        session.query(models.Shelf)
        .filter(models.Shelf.user_id == current_user.id, models.Shelf.parent_id == None)
        .all()
    )
    return shelves


@router.get("/{shelf_id}", response_model=schemas.ShelfReadWithDispatches)
def get_shelf_details(
    *,
    session: Session = Depends(get_session),
    shelf_id: int,
    current_user: models.User = Depends(get_current_user)
):
    shelf = session.get(models.Shelf, shelf_id)
    if not shelf or shelf.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Shelf not found or not authorized")
    return shelf


@router.put("/{shelf_id}", response_model=schemas.ShelfRead)
def update_shelf(
    *,
    session: Session = Depends(get_session),
    shelf_id: int,
    shelf_data: schemas.ShelfUpdate,
    current_user: models.User = Depends(get_current_user)
):
    shelf = session.get(models.Shelf, shelf_id)
    if not shelf or shelf.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Shelf not found or not authorized")

    if shelf_data.parent_id == shelf.id:
        raise HTTPException(status_code=400, detail="A shelf cannot be its own parent")

    if shelf_data.parent_id:
        parent_shelf = session.get(models.Shelf, shelf_data.parent_id)
        if not parent_shelf or parent_shelf.user_id != current_user.id:
            raise HTTPException(
                status_code=404, detail="Parent shelf not found or not authorized"
            )

    shelf.name = shelf_data.name
    shelf.parent_id = shelf_data.parent_id
    session.add(shelf)
    session.commit()
    session.refresh(shelf)
    return shelf


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shelf(
    *,
    session: Session = Depends(get_session),
    shelf_id: int,
    current_user: models.User = Depends(get_current_user)
):
    shelf = session.get(models.Shelf, shelf_id)
    if shelf and shelf.user_id == current_user.id:
        if shelf.children:
            raise HTTPException(
                status_code=400, detail="Cannot delete a shelf that has child shelves."
            )
        session.delete(shelf)
        session.commit()
    return


@router.post("/{shelf_id}/dispatches/{dispatch_id}", response_model=schemas.ShelfRead)
def add_dispatch_to_shelf(
    *,
    session: Session = Depends(get_session),
    shelf_id: int,
    dispatch_id: int,
    current_user: models.User = Depends(get_current_user)
):
    shelf = session.get(models.Shelf, shelf_id)
    if not shelf or shelf.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Shelf not found or not authorized")

    dispatch = session.get(models.Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    assignee_ids = [link.assignee_id for link in dispatch.assignee_links]
    if not current_user.is_admin and (
        dispatch.creator_id != current_user.id and current_user.id not in assignee_ids
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this dispatch"
        )

    if dispatch not in shelf.dispatches:
        shelf.dispatches.append(dispatch)
        session.add(shelf)
        session.commit()
    session.refresh(shelf)
    return shelf


@router.delete(
    "/{shelf_id}/dispatches/{dispatch_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_dispatch_from_shelf(
    *,
    session: Session = Depends(get_session),
    shelf_id: int,
    dispatch_id: int,
    current_user: models.User = Depends(get_current_user)
):
    shelf = session.get(models.Shelf, shelf_id)
    if shelf and shelf.user_id == current_user.id:
        dispatch = session.get(models.Dispatch, dispatch_id)
        if dispatch and dispatch in shelf.dispatches:
            shelf.dispatches.remove(dispatch)
            session.add(shelf)
            session.commit()
    return
