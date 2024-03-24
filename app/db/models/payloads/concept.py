from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.base_model import TimestampPayload, PyObjectId
from app.db.models.payloads.corpus import WordPayload


class ConceptPayload(TimestampPayload):
    concept_key: Optional[str] = Field(default=None, alias="key")
    root_noun: Optional[PyObjectId] = Field(default=None, alias="rootNoun")
    phrase_word_ids: Optional[list[PyObjectId]] = Field(default=None, alias="phraseWordIds")
    phrase_idxs: Optional[list[int]] = Field(default=None, alias="phraseIdxs")
    phrase_word_data: Optional[list[WordPayload]] = Field(default=None, alias="phraseWordsData")
    phrase_words: Optional[list[str]] = Field(default=None, alias="phraseWords")
    noun_count: Optional[int] = Field(default=None, alias="nounCount")
    conv_filter_idx: Optional[int] = Field(default=None, alias="convFilterIdx")

    class Config:
        _json_example = {
            "_id": ObjectId("65610d601e91b2dff82f93ba"),
            "key": "0,1",
            'rootNoun': ObjectId("656110662ce7a99311ddd94d"),
            "phraseWordIds": [ObjectId("65610d521e91b2dff82f93b9"), ObjectId("656110662ce7a99311ddd94d")],
            "phraseIdxs": [0, 1],
            "phraseWordsData": [WordPayload(), WordPayload()],
            "phraseWords": ["orange", "fur"],
            "convFilterIdx": 0,
            "nounCount": 1,
            "createdAt": datetime.now()
        }
        _json_example['updatedAt'] = _json_example['createdAt']
        json_schema_extra = {"example": _json_example}
