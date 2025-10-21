from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel):
    id: int
    full_name: str
    user_type: str
    is_admin: bool = Field(default=False)


class DispatchStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DispatchAction(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    SENT = "sent"
    STATUS_UPDATED = "status_updated"
    COMMENTED = "commented"
    FORWARDED = "forwarded"


class DispatchShelfLink(SQLModel, table=True):
    dispatch_id: Optional[int] = Field(
        default=None, foreign_key="dispatch.id", primary_key=True
    )
    shelf_id: Optional[int] = Field(
        default=None, foreign_key="shelf.id", primary_key=True
    )


class DispatchAssigneeLink(SQLModel, table=True):
    dispatch_id: Optional[int] = Field(
        default=None, foreign_key="dispatch.id", primary_key=True
    )
    assignee_id: int = Field(primary_key=True, index=True)
    dispatch: "Dispatch" = Relationship(back_populates="assignee_links")


class Shelf(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    user_id: int = Field(index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="shelf.id")
    parent: Optional["Shelf"] = Relationship(
        back_populates="children", sa_relationship_kwargs=dict(remote_side="Shelf.id")
    )
    children: List["Shelf"] = Relationship(back_populates="parent")
    dispatches: List["Dispatch"] = Relationship(
        back_populates="shelves", link_model=DispatchShelfLink
    )


class DispatchFile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_url: str
    filename: str
    dispatch_id: int = Field(foreign_key="dispatch.id")
    dispatch: "Dispatch" = Relationship(back_populates="files")


class DispatchHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action: DispatchAction
    details: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor_id: int
    dispatch_id: int = Field(foreign_key="dispatch.id")
    dispatch: "Dispatch" = Relationship(back_populates="history")


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: int
    dispatch_id: int = Field(foreign_key="dispatch.id")
    dispatch: "Dispatch" = Relationship(back_populates="comments")


class Dispatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    status: DispatchStatus = Field(default=DispatchStatus.DRAFT)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    creator_id: int
    files: List[DispatchFile] = Relationship(
        back_populates="dispatch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    history: List[DispatchHistory] = Relationship(
        back_populates="dispatch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    comments: List[Comment] = Relationship(
        back_populates="dispatch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    shelves: List[Shelf] = Relationship(
        back_populates="dispatches", link_model=DispatchShelfLink
    )
    assignee_links: List[DispatchAssigneeLink] = Relationship(
        back_populates="dispatch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
