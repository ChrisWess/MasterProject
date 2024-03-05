from typing import Annotated, Optional

from bson import ObjectId
from pydantic import Field, StringConstraints, NonNegativeInt, BaseModel

from app.db.models.base_model import DataBaseModel, PyObjectId


class NounChunk(BaseModel):
    """ If a word is the first word in a noun chunk, it gets a NounChunk attached """
    word_ids: list[PyObjectId] = Field(alias="wordIDs")  # referring to other words
    is_proper: bool = Field(default=True, alias="isProper")

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        populate_by_name = True
        _json_example = {
            "wordIDs": [0, 1],
            "isProper": True,
        }
        json_schema_extra = {"example": _json_example}

    def to_dict(self):
        return self.model_dump(by_alias=True)

    def to_json(self):
        return self.model_dump_json(by_alias=True)


class CorpusWord(DataBaseModel):
    """
    Corpus contains the words (only nouns and adjectives) of all phrases in the dataset.
    Words in the corpus must not necessarily be present in any concept doc of the database.
    """
    # Could add support for other languages (=> add attribute lang e.g. lang="de")
    index_val: NonNegativeInt = Field(
        alias="index")  # TODO: Same lemmas get same index. Use ID if exact match required!
    text: Annotated[str, StringConstraints(min_length=1, max_length=30,
                                           strip_whitespace=True, to_lower=True)]  # lower-case word
    lemma: Annotated[str, StringConstraints(min_length=1, max_length=30, strip_whitespace=True, to_lower=True)]
    # https://stackabuse.com/python-for-nlp-tokenization-stemming-and-lemmatization-with-spacy-library/
    stem: Optional[Annotated[str, StringConstraints(min_length=1, max_length=30,
                                                    strip_whitespace=True, to_lower=True)]] = None
    # TODO: Connect synonyms by index. How to identify them?
    #  https://www.sean-holt.com/single-post/2018/11/04/Using-SpaCy-to-Generate-Synonyms-and-Grammatical-Variations
    #  https://stackoverflow.com/questions/54717449/mapping-word-vector-to-the-most-similar-closest-word-using-spacy

    # TODO: counts/count_per_class/tf-idf could be used for ranking in full-text search.
    #  Nouns should probably also be ranked a bit higher than adjectives.
    noun_flag: bool = Field(alias="nounFlag")
    noun_chunks: Optional[list[NounChunk]] = Field(default=None, alias="nounChunks")

    class Config:
        _json_example = {
            "_id": ObjectId("65610d521e91b2dff82f93b9"),
            "index": 0,
            "text": "fur",
            "stem": "fur",
            "lemma": "fur",
            "nounFlag": True,
        }
        json_schema_extra = {"example": _json_example}
