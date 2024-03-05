from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.base_model import TimestampPayload, PayloadBaseModel, PyObjectId
from app.db.models.user import UserRole


class UserPayload(PayloadBaseModel):
    name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    hashed_pass: Optional[bytes] = Field(default=None, alias="hashedPass")
    role: Optional[UserRole] = Field(default=None)
    color: Optional[str] = Field(default=None)
    active: Optional[bool] = Field(default=None)

    def __init__(self, **data):
        if 'role' in data:
            data['role'] = UserRole(data['role'])
        super().__init__(**data)

    class Config:
        use_enum_values = True
        json_exclude = {"hashed_pass"}
        _json_example = {
            "_id": ObjectId("6560badba00004fb3359631f"),
            "name": "Max Mustermann",
            "email": "max.mustermann@email.de",
            "hashedPass": b"<hidden>",
            "role": 1,
            "color": "#3a7b25",
            "active": True
        }
        json_schema_extra = {"example": _json_example}

    def to_dict(self):
        return self.model_dump(exclude=self.Config.json_exclude, exclude_unset=True, by_alias=True)


class UserCreationPayload(TimestampPayload):
    created_by: Optional[PyObjectId] = Field(default=None, alias="createdBy")
    creator: Optional[UserPayload] = Field(default=None)
