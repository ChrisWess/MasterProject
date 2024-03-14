from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.base_model import PyObjectId
from app.db.models.payloads.concept import ConceptPayload
from app.db.models.payloads.user import UserCreationPayload, UserPayload


class AnnotationPayload(UserCreationPayload):
    text: Optional[str] = Field(default=None)
    tokens: Optional[list[str]] = Field(default=None)
    concept_mask: Optional[list[int]] = Field(default=None, alias="conceptMask")
    concept_ids: Optional[list[PyObjectId]] = Field(default=None, alias="conceptIds")
    concepts: Optional[list[ConceptPayload]] = Field(default=None)

    class Config:
        _json_example = {
            "_id": ObjectId("6560badba00004fb3359631e"),
            "text": "This is a fox, because it has orange fur.",
            "tokens": ["this", "is", "a", "fox", ",", "because", "it", "has", "orange", "fur"],
            "conceptMask": [-1, -1, -1, -1, -1, -1, -1, -1, 0, 0],  # ints >= 0 denote concepts
            "conceptIds": [ObjectId("65610d601e91b2dff82f93ba")],
            "concepts": [ConceptPayload.Config._json_example],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "creator": UserPayload.Config._json_example,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
