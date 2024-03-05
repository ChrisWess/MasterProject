from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import Field, StringConstraints

from app.db.models.base_model import UserCreationModel, PyObjectId


class Annotation(UserCreationModel):
    # Could add support for other languages (=> add attribute lang e.g. lang="de")
    text: Annotated[str, StringConstraints(min_length=10, max_length=1000, strip_whitespace=True)]  # textual expl
    tokens: list[str] = Field(default_factory=list)  # tokenized annotation
    concept_mask: list[int] = Field(default_factory=list, alias="conceptMask")  # which tokens belong to which concept
    concept_ids: list[PyObjectId] = Field(default_factory=list, alias="conceptIds")

    # TODO: new field "isGenerated"

    # TODO: add a list of "concept segments", where each describes an area in the object's image that correspond
    #  to the region where the model identified the concept to be at (retrieved from neural activation map).
    #  When the concept does not have a corresponding conv filter in the model (yet), then it should be None
    #  by default, but in the future a user could mark the part where the concept should be located at.
    #  Users should be able to draw polygons, the activation pixel-blobs should also be simplified to polygons.

    class Config:
        _json_example = {
            "_id": ObjectId("6560badba00004fb3359631e"),
            "text": "This is a fox, because it has orange fur.",
            "tokens": ["this", "is", "a", "fox", ",", "because", "it", "has", "orange", "fur"],
            # If present, label/class tokens get a special value of: - labelIdx - 2
            "conceptMask": [-1, -1, -1, -2, -1, -1, -1, -1, 0, 0],  # ints >= 0 denote concepts
            "conceptIds": [ObjectId("65610d601e91b2dff82f93ba")],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
