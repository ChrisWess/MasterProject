from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.base_model import TimestampBaseModel, PyObjectId


class WorkEntry(TimestampBaseModel):
    worker_id: PyObjectId = Field(alias="workerId")
    doc_id: PyObjectId = Field(alias="docId")
    project_id: Optional[PyObjectId] = Field(alias="projectId", default=None)
    is_Finished: bool = Field(alias="isFinished", default=False)

    class Config:
        _json_example = {
            "_id": ObjectId("65610d371e91b2dff82f93a5"),
            "workerId": ObjectId("6560badba00004fb3359631f"),
            "docId": ObjectId("6560e23ce1a3e3df0863b6d8"),
            "projectId": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "isFinished": False,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
