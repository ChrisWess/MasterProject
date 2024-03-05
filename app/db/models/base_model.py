from datetime import datetime
from typing import Annotated, Union, Any

from bson import ObjectId
from pydantic import BaseModel, Field, AfterValidator, root_validator


def validate_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[
    Union[str, ObjectId],
    AfterValidator(validate_object_id),
]


class DataBaseModel(BaseModel):
    id: PyObjectId = Field(alias="_id", default=None)

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        populate_by_name = True

    @classmethod
    def postprocess_insert_response(cls, model_dict, inserted_id):
        model_dict['_id'] = str(inserted_id)
        return model_dict

    def to_dict(self):
        return self.model_dump(exclude='id', by_alias=True)

    def to_json(self):
        return self.model_dump_json(by_alias=True)


class TimestampBaseModel(DataBaseModel):
    created_at_ts: datetime = Field(default_factory=datetime.now, alias="createdAt")
    updated_at_ts: datetime = Field(default=None, alias="updatedAt")

    # TODO: could also keep track of the total number of updates

    def __init__(self, **data):
        if 'createdAt' in data and isinstance(data['createdAt'], str):
            data['createdAt'] = self.serialize_datetime(data['createdAt'])
        if 'updatedAt' in data and isinstance(data['updatedAt'], str):
            data['updatedAt'] = self.serialize_datetime(data['updatedAt'])
        super().__init__(**data)

    @staticmethod
    def serialize_datetime(ts):
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")

    @root_validator(skip_on_failure=True)
    def get_address(cls, values) -> dict:
        # This was already deprecated when I implemented it, but nothing else worked for me!
        if values.get("updated_at_ts") is None:
            # Having always at least the updatedAt value at the creation time (even though no update was
            # necessarily executed) is nice for data/schema consistency and is desirable for better sorting.
            values["updated_at_ts"] = values.get("created_at_ts")
        return values


class UserCreationModel(TimestampBaseModel):
    created_by: PyObjectId = Field(alias="createdBy")
