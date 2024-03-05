from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.base_model import TimestampPayload, PyObjectId
from app.db.models.payloads.image_doc import ImagePayload
from app.db.models.payloads.project import ProjectPayload
from app.db.models.payloads.user import UserPayload


class WorkEntryPayload(TimestampPayload):
    worker_id: Optional[PyObjectId] = Field(alias="workerId", default=None)
    worker: Optional[UserPayload] = None
    doc_id: Optional[PyObjectId] = Field(alias="docId", default=None)
    document: Optional[ImagePayload] = None
    project_id: Optional[PyObjectId] = Field(alias="projectId", default=None)
    project: Optional[ProjectPayload] = None
    is_Finished: Optional[bool] = Field(alias="isFinished", default=None)

    class Config:
        _json_example = {
            "_id": ObjectId("65610d371e91b2dff82f93a5"),
            "workerId": ObjectId("6560badba00004fb3359631f"),
            "worker": UserPayload.Config._json_example,
            "docId": ObjectId("6560e23ce1a3e3df0863b6d8"),
            "document": ImagePayload.Config._json_example,
            "projectId": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "project": ProjectPayload.Config._json_example,
            "isFinished": False,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
