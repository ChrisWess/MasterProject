from datetime import datetime
from typing import Annotated, Optional

from bson import ObjectId
from pydantic import Field, StringConstraints, PositiveInt, model_validator

from app.db.models.base_model import UserCreationModel, DataBaseModel, PyObjectId
from app.db.models.object import DetectedObject


class ImgDoc(UserCreationModel):
    project_id: Optional[PyObjectId] = Field(alias="projectId", default=None)
    name: Annotated[str, StringConstraints(min_length=2, max_length=100, strip_whitespace=True)]
    fname: Annotated[str, StringConstraints(min_length=4, max_length=50)]
    thumbnail: Optional[PyObjectId] = None
    image: Optional[PyObjectId] = None
    # TODO: compute a hash function given the image (or maybe just given thumbnail to be even more efficient)
    #  in order to detect duplicate images. Depending on the nature of the hash function, saving the hash value
    #  in the DB might be handy for other reasons in the future (e.g. sorting, clustering or other analysis)
    width: PositiveInt  # pixel width of the image
    height: PositiveInt  # pixel height of the image
    objects: list[DetectedObject] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_all_bboxes_valid(self):
        if self.objects:
            for i, obj in enumerate(self.objects):
                if obj.bbox_botright_x > self.width:
                    raise ValueError(f"The width of the {i}. object exceeds the width of its root image!")
                if obj.bbox_botright_y > self.height:
                    raise ValueError(f"The height of the {i}. object exceeds the height of its root image!")
        return self

    class Config:
        json_exclude = {"thumbnail", "image"}
        _json_example = {
            "_id": ObjectId("6560e23ce1a3e3df0863b6d8"),
            "projectId": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "name": "A fox jumping over a yellow fence",
            "fname": "fox.jpg",
            "thumbnail": ObjectId("658c8387d284a741062ec0ab"),
            "image": ObjectId("658c8387d284a741062ec0aa"),  # reference to the gridfs file
            "width": 1920,
            "height": 1080,
            "prio": 1.0,
            "objects": [DetectedObject.Config._json_example],
            "createdBy": ObjectId("6560badba00004fb3359631f"),
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}

    @classmethod
    def postprocess_insert_response(cls, model_dict, db_insert):
        for e in cls.Config.json_exclude:
            model_dict.pop(e, None)
        return DataBaseModel.postprocess_insert_response(model_dict, db_insert)

    def to_json(self):
        return self.model_dump_json(exclude=self.Config.json_exclude, by_alias=True)
