from . import models, schemas


def convert_dispatch_to_read_model(dispatch: models.Dispatch) -> schemas.DispatchRead:
    """Constructs the DispatchRead schema from the DB model."""
    return schemas.DispatchRead(
        id=dispatch.id,
        title=dispatch.title,
        content=dispatch.content,
        status=dispatch.status,
        created_at=dispatch.created_at,
        creator_id=dispatch.creator_id,
        assignee_ids=[link.assignee_id for link in dispatch.assignee_links],
    )


def convert_dispatch_to_detailed_read_model(
    dispatch: models.Dispatch,
) -> schemas.DispatchReadWithDetails:
    """Constructs the DispatchReadWithDetails schema from the DB model."""
    # This is necessary because SQLModel/Pydantic can't automatically
    # populate `assignee_ids` from the `assignee_links` relationship.
    return schemas.DispatchReadWithDetails(
        id=dispatch.id,
        title=dispatch.title,
        content=dispatch.content,
        status=dispatch.status,
        created_at=dispatch.created_at,
        creator_id=dispatch.creator_id,
        assignee_ids=[link.assignee_id for link in dispatch.assignee_links],
        files=dispatch.files,
        history=dispatch.history,
        comments=dispatch.comments,
        # Convert each shelf model to a shelf read schema
        shelves=[schemas.ShelfRead.model_validate(s) for s in dispatch.shelves],
    )
