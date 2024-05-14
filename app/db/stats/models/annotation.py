from datetime import datetime

from bson import ObjectId
from pydantic import Field, NonNegativeInt, NonNegativeFloat, BaseModel

from app.db.models.payloads.concept import ConceptPayload
from app.db.models.payloads.label import LabelPayload
from app.db.stats.models.base_stats import StatsBase


class UnrolledConceptCountsStat(BaseModel):
    concept: ConceptPayload = Field(default=None)
    label: LabelPayload = Field(default=None)
    count: NonNegativeInt = Field(default=0)

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        populate_by_name = True

    def to_dict(self):
        return self.model_dump(exclude_none=True)


class VectorizedCountsStat(StatsBase):
    count: NonNegativeInt = Field(default=0)

    class Config:
        _json_example = {
            "_id": {'concept': ObjectId("65fffa22f3e9f8fe71cd9d20"), 'label': ObjectId("66097eb92cd30218c3c96494")},
            "isValid": False,
            "count": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}


class DocOccurrenceCountStat(StatsBase):
    occurrence_count: NonNegativeInt = Field(default=0, alias='occurrenceCount')

    class Config:
        _json_example = {
            "_id": ObjectId("65fffa22f3e9f8fe71cd9d20"),
            "isValid": False,
            "occurrenceCount": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}


class TfIdfStat(StatsBase):
    tf_idf: NonNegativeFloat = Field(default=0., alias='tfIdf')

    class Config:
        _json_example = {
            "_id": {"concept": ObjectId("65fffa22f3e9f8fe71cd9d20"), "label": ObjectId("66097eb92cd30218c3c96494")},
            "isValid": False,
            "tfIdf": 0.,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}


class TopImgConceptsStat(StatsBase):
    label: ObjectId = Field(default=None)
    topConcepts: list[ObjectId] = Field(default_factory=list, alias='topConcepts')

    class Config:
        _json_example = {
            "_id": ObjectId("6560e23ce1a3e3df0863b6d8"),
            "isValid": False,
            "label": ObjectId("66097eb92cd30218c3c96494"),
            'topConcepts': [ObjectId("65fffa22f3e9f8fe71cd9d20")],
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
