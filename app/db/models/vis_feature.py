from datetime import datetime

from bson import ObjectId
from pydantic import Field, BaseModel, NonNegativeInt, model_validator

from app.db.models.base_model import UserCreationModel, PyObjectId


# TODO: Features as next layer below the objects (with their own bounding boxes):
#   Annotators have to provide the visual features on the objects during the annotation of an object
# TODO: should these features be nested in an object?

class BoundingBox(BaseModel):
    topleft_x: NonNegativeInt = Field(alias="tlx")
    topleft_y: NonNegativeInt = Field(alias="tly")
    botright_x: NonNegativeInt = Field(alias="brx")
    botright_y: NonNegativeInt = Field(alias="bry")

    @model_validator(mode='after')
    def check_bbox(self):
        if self.topleft_x >= self.botright_x:
            raise ValueError("x values of the two corner points were provided in the wrong order! "
                             f"Left x: {self.topleft_x} ; Right x: {self.botright_x}")
        if self.topleft_y >= self.botright_y:
            raise ValueError("y values of the two corner points were provided in the wrong order! "
                             f"Upper y: {self.topleft_y} ; Lower y: {self.botright_y}")
        return self

    class Config:
        _json_example = {
            "tlx": 0, "tly": 0,
            "brx": 100, "bry": 100,
        }
        json_schema_extra = {"example": _json_example}

    def to_dict(self):
        return self.model_dump(by_alias=True)


class VisualFeature(UserCreationModel):
    annotation_id: PyObjectId = Field(alias="annotationId")
    concept_id: PyObjectId = Field(alias="conceptId")
    # Bounding boxes are defined with respect to coordinates of the object's bounding box
    bboxs: list[BoundingBox] = Field(default_factory=list)

    def __init__(self, **data):
        if 'bboxs' in data:
            bboxs = data['bboxs']
            for i, bbox in enumerate(bboxs):
                if isinstance(bbox, list):
                    bboxs[i] = BoundingBox(tlx=bbox[0], tly=bbox[1], brx=bbox[2], bry=bbox[3])
        super().__init__(**data)

    class Config:
        _json_example = {
            "_id": ObjectId("65ac01674e1ed269cbe2f9e7"),
            "annotationId": ObjectId("6560badba00004fb3359631e"),
            "conceptId": ObjectId("65610d601e91b2dff82f93ba"),
            "bboxs": [BoundingBox.Config._json_example],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
