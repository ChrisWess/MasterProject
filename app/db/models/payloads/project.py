from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.base_model import PyObjectId
from app.db.models.payloads.image_doc import ImagePayload
from app.db.models.payloads.user import UserCreationPayload, UserPayload


class ProjectPayload(UserCreationPayload):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    doc_ids: Optional[list[PyObjectId]] = Field(default=None, alias="docIds")
    documents: Optional[list[ImagePayload]] = None
    member_ids: Optional[list[PyObjectId]] = Field(default=None, alias="memberIds")
    members: Optional[list[UserPayload]] = None

    class Config:
        example_user = UserPayload.Config._json_example
        _json_example = {
            "_id": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "title": 'Test Project',
            'description': 'This is a demo project.',
            'tags': ['demo', 'test'],
            "docIds": [ObjectId("6560e23ce1a3e3df0863b6d8")],
            "documents": [ImagePayload.Config._json_example],
            "memberIds": [ObjectId("6560badba00004fb3359631f")],
            "members": [example_user],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "creator": example_user,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
