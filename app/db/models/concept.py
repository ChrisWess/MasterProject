from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field, NonNegativeInt

from app.db.models.base_model import TimestampBaseModel, PyObjectId


class Concept(TimestampBaseModel):
    # TODO: perhaps add compatibility to save concepts with a sort of thumbnail image
    concept_key: str = Field(alias="key")
    root_noun: PyObjectId = Field(alias="rootNoun")
    phrase_word_ids: list[PyObjectId] = Field(default_factory=list, alias="phraseWordIds")  # list of corpus word IDs
    phrase_idxs: list[int] = Field(default_factory=list, alias="phraseIdxs")
    phrase_words: list[str] = Field(default_factory=list, alias="phraseWords")
    complex_noun: bool = Field(default=False, alias="isNounComplex")
    # By setting the following as -1, we can denote that the phrase is not relevant to the model (not modelled)
    conv_filter_idx: Optional[NonNegativeInt] = Field(default=None, alias="convFilterIdx")

    class Config:
        _json_example = {
            "_id": ObjectId("65610d601e91b2dff82f93ba"),
            "key": "0,1",
            'rootNoun': ObjectId("656110662ce7a99311ddd94d"),
            "phraseWordIds": [ObjectId("65610d521e91b2dff82f93b9"), ObjectId("656110662ce7a99311ddd94d")],
            "phraseIdxs": [0, 1],
            "phraseWords": ["orange", "fur"],  # adjectives come first
            "convFilterIdx": 0,  # index of the model's conv-filter for this concept
            "isNounComplex": False,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
