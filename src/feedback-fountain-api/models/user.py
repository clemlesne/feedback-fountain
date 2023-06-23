from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class UserModel(BaseModel):
    created: datetime = None
    dummy: str = "dummy" # Partition key
    id: UUID = None
    username: str
