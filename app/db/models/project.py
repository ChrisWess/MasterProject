from datetime import datetime
from typing import Optional, Annotated

from bson import ObjectId
from pydantic import Field, StringConstraints

from app.db.models.base_model import UserCreationModel, PyObjectId


class Project(UserCreationModel):
    title: Annotated[str, StringConstraints(min_length=3, max_length=50, strip_whitespace=True)]
    description: Optional[Annotated[str, StringConstraints(min_length=1, max_length=500, strip_whitespace=True)]] = None
    tags: list[Annotated[str, StringConstraints(min_length=2, max_length=20,
                                                strip_whitespace=True, to_lower=True)]] = Field(default_factory=list)
    doc_ids: list[PyObjectId] = Field(default_factory=list, alias="docIds")
    member_ids: list[PyObjectId] = Field(default_factory=list, alias="memberIds")

    class Config:
        _json_example = {
            "_id": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "title": 'Test Project',
            'description': 'This is a demo project.',
            'tags': ['demo', 'test'],
            "docIds": [ObjectId("6560e23ce1a3e3df0863b6d8")],
            "memberIds": [ObjectId("6560badba00004fb3359631f")],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
