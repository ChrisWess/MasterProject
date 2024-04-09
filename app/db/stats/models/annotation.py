from datetime import datetime

from bson import ObjectId
from pydantic import Field, NonNegativeInt, NonNegativeFloat

from app.db.stats.models.base_stats import StatsBase


class AnnotationConceptCountStat(StatsBase):
    concept_count: NonNegativeInt = Field(default=0, alias="conceptCount")

    class Config:
        _json_example = {
            "_id": {'concept': ObjectId("65fffa22f3e9f8fe71cd9d20"), 'label': ObjectId("66097eb92cd30218c3c96494")},
            "isValid": False,
            "conceptCount": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}


class AnnotationWordCountStat(StatsBase):
    word_count: NonNegativeInt = Field(default=0, alias="wordIdxCount")

    class Config:
        _json_example = {
            "_id": {'wordIdx': 0, 'label': ObjectId("66097eb92cd30218c3c96494"), 'isNoun': False},
            "isValid": False,
            "wordIdxCount": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}


class DocOccurrenceCountStat(StatsBase):
    occurrence_count: NonNegativeInt = Field(default=0, alias='occurenceCount')

    class Config:
        _json_example = {
            "_id": ObjectId("65fffa22f3e9f8fe71cd9d20"),
            "isValid": False,
            "occurenceCount": 0,
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
