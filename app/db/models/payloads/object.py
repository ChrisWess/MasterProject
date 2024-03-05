from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.annotation import AnnotationPayload
from app.db.models.payloads.base_model import PyObjectId
from app.db.models.payloads.label import LabelPayload
from app.db.models.payloads.user import UserCreationPayload, UserPayload


class ObjectPayload(UserCreationPayload):
    label_id: Optional[PyObjectId] = Field(default=None, alias="labelId")
    label: Optional[LabelPayload] = Field(default=None)
    annotations: Optional[list[AnnotationPayload]] = Field(default=None)
    bbox_topleft_x: Optional[int] = Field(default=None, alias="tlx")
    bbox_topleft_y: Optional[int] = Field(default=None, alias="tly")
    bbox_botright_x: Optional[int] = Field(default=None, alias="brx")
    bbox_botright_y: Optional[int] = Field(default=None, alias="bry")

    class Config:
        _json_example = {
            "_id": ObjectId("6560bb8c49d58b986276c630"),
            "labelId": ObjectId("65610d371e91b2dff82f93b8"),
            "label": LabelPayload.Config._json_example,
            "annotations": [AnnotationPayload.Config._json_example],
            "tlx": 0, "tly": 0,
            "brx": 100, "bry": 100,
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "creator": UserPayload.Config._json_example,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
