from datetime import datetime
from enum import Enum
from typing import List, Optional, Generic, TypeVar
from sqlmodel import SQLModel
from .models import DispatchStatus, DispatchFile, DispatchHistory, Comment


# --- Shelf Schemas ---
class ShelfCreate(SQLModel):
    name: str
    parent_id: Optional[int] = None


class ShelfUpdate(SQLModel):
    name: str
    parent_id: Optional[int] = None


class ShelfRead(SQLModel):
    id: int
    name: str
    user_id: int
    parent_id: Optional[int] = None


class ShelfReadWithChildren(ShelfRead):
    children: List["ShelfReadWithChildren"] = []


# --- Dispatch Schemas ---
class DispatchCore(SQLModel):
    title: str
    content: str


class DispatchBase(DispatchCore):
    status: DispatchStatus
    created_at: datetime
    creator_id: int


class DispatchCreate(DispatchCore):
    assignee_ids: List[int]
    files: List[str]


class DispatchUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    assignee_ids: Optional[List[int]] = None


class DispatchRead(DispatchBase):
    id: int
    assignee_ids: List[int]


class ShelfReadWithDispatches(ShelfReadWithChildren):
    dispatches: List[DispatchRead] = []


class DispatchReadWithDetails(DispatchRead):
    files: List[DispatchFile] = []
    history: List[DispatchHistory] = []
    comments: List[Comment] = []
    shelves: List[ShelfRead] = []


class DispatchStatusUpdateEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DispatchStatusUpdate(SQLModel):
    status: DispatchStatusUpdateEnum


class DispatchForward(SQLModel):
    new_assignee_id: int


class CommentCreate(SQLModel):
    content: str


# --- Generic & Statistics Schemas ---
T = TypeVar("T")


class PaginatedResponse(SQLModel, Generic[T]):
    total: int
    items: List[T]


class MyStats(SQLModel):
    incoming: int
    outgoing: int
    status_counts: dict[DispatchStatus, int]


class UserActivityStat(SQLModel):
    user_id: int
    count: int


class SystemStats(SQLModel):
    total_dispatches: int
    status_counts: dict[DispatchStatus, int]
    top_creators: List[UserActivityStat]
    top_assignees: List[UserActivityStat]


# Rebuild models to resolve forward references
# This is crucial for FastAPI's OpenAPI schema generation to work correctly.
ShelfReadWithChildren.model_rebuild()
DispatchReadWithDetails.model_rebuild()
ShelfReadWithDispatches.model_rebuild()
