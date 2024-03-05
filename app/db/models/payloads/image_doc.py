from datetime import datetime
from typing import Optional, Any, Union, Annotated

from bson import ObjectId
from pydantic import Field, AfterValidator

from app import fs
from app.db.models.payloads.base_model import PyObjectId
from app.db.models.payloads.object import ObjectPayload
from app.db.models.payloads.user import UserCreationPayload, UserPayload
from app.db.util import encode_as_base64


def validate_bytes(b: Any) -> str:
    if isinstance(b, bytes):
        return encode_as_base64(b)
    if isinstance(b, str):
        return b
    raise ValueError("Invalid Bytes input")


Base64 = Annotated[
    Union[bytes, str],
    AfterValidator(validate_bytes),
]


class ImagePayload(UserCreationPayload):
    project_id: Optional[PyObjectId] = Field(alias="projectId", default=None)
    name: Optional[str] = Field(default=None)
    fname: Optional[str] = Field(default=None)
    thumbnail: Optional[Base64] = Field(default=None)
    image: Optional[Base64] = Field(default=None)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    objects: Optional[list[ObjectPayload]] = Field(default=None)

    def __init__(self, **data):
        thumb = data.get('thumbnail', None)
        if thumb and isinstance(thumb, ObjectId):
            data['thumbnail'] = fs.get(thumb).read()
        image = data.get('image', None)
        if image and isinstance(image, ObjectId):
            data['image'] = fs.get(image).read()
        super().__init__(**data)

    class Config:
        # ser_json_bytes = 'base64'  # Note: this config does not work
        json_exclude = {"thumbnail", "image"}
        example_user = UserPayload.Config._json_example
        _json_example = {
            "_id": ObjectId("6560e23ce1a3e3df0863b6d8"),
            "projectId": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "name": "A fox jumping over a yellow fence",
            "fname": "fox.jpg",
            "thumbnail": 'base64 string',
            "image": 'base64 string',
            "width": 1920,
            "height": 1080,
            "objects": [ObjectPayload.Config._json_example],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "creator": example_user,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
