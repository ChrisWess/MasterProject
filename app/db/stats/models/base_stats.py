from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

from app.db.models.base_model import PyObjectId


class StatsBase(BaseModel):
    id: Union[PyObjectId, dict] = Field(alias="_id", default=None)
    is_valid: bool = Field(alias="isValid", default=True)
    updated_at_ts: datetime = Field(default_factory=datetime.now, alias="updatedAt")

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        populate_by_name = True

    def to_dict(self):
        return self.model_dump(exclude='_id', by_alias=True)

    def to_json(self):
        return self.model_dump_json(exclude='is_valid', by_alias=True)
