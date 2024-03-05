from datetime import datetime

from bson import ObjectId
from pydantic import Field, NonNegativeInt, model_validator

from app.db.models.annotation import Annotation
from app.db.models.base_model import UserCreationModel, PyObjectId


class DetectedObject(UserCreationModel):
    label_id: PyObjectId = Field(alias="labelId")
    annotations: list[Annotation] = Field(default_factory=list)
    # Bounding box in the doc-image as 2 xy-points (following 4 fields)
    bbox_topleft_x: NonNegativeInt = Field(alias="tlx")
    bbox_topleft_y: NonNegativeInt = Field(alias="tly")
    bbox_botright_x: NonNegativeInt = Field(alias="brx")
    bbox_botright_y: NonNegativeInt = Field(alias="bry")

    @model_validator(mode='after')
    def check_bbox(self):
        if self.bbox_topleft_x >= self.bbox_botright_x:
            raise ValueError("x values of the two corner points were provided in the wrong order! "
                             f"Left x: {self.bbox_topleft_x} ; Right x: {self.bbox_botright_x}")
        if self.bbox_topleft_y >= self.bbox_botright_y:
            raise ValueError("y values of the two corner points were provided in the wrong order! "
                             f"Upper y: {self.bbox_topleft_y} ; Lower y: {self.bbox_botright_y}")
        return self

    class Config:
        """ "bbox" should be a tuple with 2 coordinate points top-left: (x_1, y_1) and bottom-right: (x_2, y_2). """
        _json_example = {
            "_id": ObjectId("6560bb8c49d58b986276c630"),
            "labelId": ObjectId("65610d371e91b2dff82f93b8"),
            "annotations": [Annotation.Config._json_example],
            "tlx": 0, "tly": 0,
            "brx": 100, "bry": 100,
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
