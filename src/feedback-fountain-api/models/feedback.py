from datetime import datetime
from pydantic import BaseModel
from typing import List
from uuid import UUID


class FeedbackModel(BaseModel):
    content: str
    created: datetime = None
    id: UUID = None
    owner: UUID # Partition key
    tags: List[str]
    title: str


class SearchFeedbackModel(BaseModel):
    feedbacks: List[FeedbackModel]
