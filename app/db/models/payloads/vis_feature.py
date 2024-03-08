from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.annotation import AnnotationPayload
from app.db.models.payloads.base_model import PyObjectId
from app.db.models.payloads.concept import ConceptPayload
from app.db.models.payloads.user import UserCreationPayload, UserPayload
from app.db.models.vis_feature import BoundingBox


class VisualFeaturePayload(UserCreationPayload):
    object_id: Optional[PyObjectId] = Field(alias="objectId")
    annotation_id: Optional[PyObjectId] = Field(alias="annotationId")
    annotation: Optional[AnnotationPayload] = Field(default=None)
    concept_id: Optional[PyObjectId] = Field(default=None, alias="conceptId")
    concept: Optional[ConceptPayload] = Field(default=None)
    bboxs: Optional[list[BoundingBox]] = Field(default=None)

    class Config:
        _json_example = {
            "_id": ObjectId("65ac01674e1ed269cbe2f9e7"),
            "objectId": ObjectId("6560bb8c49d58b986276c630"),
            "annotationId": ObjectId("6560badba00004fb3359631e"),
            "annotation": AnnotationPayload.Config._json_example,
            "conceptId": ObjectId("65610d601e91b2dff82f93ba"),
            "concept": ConceptPayload.Config._json_example,
            "bboxs": [BoundingBox.Config._json_example],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "creator": UserPayload.Config._json_example,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
