from datetime import datetime
from typing import Optional, Annotated, Union

from bson import ObjectId
from pydantic import BaseModel, Field, AfterValidator, PlainSerializer, WithJsonSchema

from app.db.models.base_model import validate_object_id

PyObjectId = Annotated[
    Union[str, ObjectId],
    AfterValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class PayloadBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        populate_by_name = True

    def to_dict(self):
        return self.model_dump(exclude_unset=True, by_alias=True)

    def to_json(self):
        return self.model_dump_json(exclude_unset=True, by_alias=True)


class TimestampPayload(PayloadBaseModel):
    updated_at_ts: Optional[datetime] = Field(default=None, alias="updatedAt")
    created_at_ts: Optional[datetime] = Field(default=None, alias="createdAt")
