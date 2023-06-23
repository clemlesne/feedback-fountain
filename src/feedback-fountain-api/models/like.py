from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from typing import List


class LikeModel(BaseModel):
    created: datetime = None
    id: UUID = None
    related: UUID # Partition key
    user: UUID


class SearchLikeModel(BaseModel):
    likes: List[LikeModel]
