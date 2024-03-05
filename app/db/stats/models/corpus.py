from datetime import datetime
from typing import Optional, Dict

from bson import ObjectId
from pydantic import Field, NonNegativeInt

from app.db.models.payloads.base_model import PyObjectId
from app.db.stats.models.base_stats import StatsBase


class CorpusStats(StatsBase):
    word_id: PyObjectId = Field(alias="wordId", default=None)
    index_val: NonNegativeInt = Field(alias="index")
    count: NonNegativeInt = 1  # number of occurrences in the entire dataset of explanations
    count_per_class: Optional[Dict[int, int]] = Field(default=None, alias="countPerClass")
    in_num_phrases: NonNegativeInt = Field(default=0, alias="occurInPhrases")  # number of occurrences in saved concepts

    # TODO: also save a tf-idf for each word

    class Config:
        _json_example = {
            "_id": "corpus_word_stats",
            "isValid": False,
            "wordId": ObjectId("65610d601e91b2dff82f93ba"),
            "index": 0,
            "count": 1,
            "countPerClass": {0: 1},
            "occurInPhrases": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
