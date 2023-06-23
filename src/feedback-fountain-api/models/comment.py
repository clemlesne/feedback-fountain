from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from typing import List


class CommentModel(BaseModel):
    content: str
    created: datetime = None
    id: UUID = None
    related: UUID # Partition key
    user: UUID


class SearchCommentModel(BaseModel):
    comments: List[CommentModel]
