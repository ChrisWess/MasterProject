from pymongo import DESCENDING

from app import mdb, application
from app.db.daos.base import AbstractDAO


class IndexManager(AbstractDAO):
    __slots__ = "id", "seq_key", "index_dbref", "index_field", "counter_id", "incrementer", "multi_incrementer"

    def __init__(self, index_dbref, index_field=None):
        super().__init__('counters')
        self.id = f"{index_dbref}_idx"
        self.seq_key = "sequence_value"
        self.index_dbref = index_dbref
        self.index_field = index_dbref[:-1] + 'Idx' if index_field is None else index_field
        self.counter_id = {"_id": self.id}
        self.incrementer = {"$inc": {self.seq_key: 1}}
        self.multi_incrementer = {"$inc": {self.seq_key: 0}}
        self._validate_counter()

    def _validate_counter(self):
        highest_idx = getattr(mdb, self.index_dbref).find().sort([(self.index_field, DESCENDING)]).limit(1)
        try:
            highest_idx = highest_idx.next()[self.index_field]
        except StopIteration:
            highest_idx = -1
        # Check if the counters exist & if they match the indices for labels and words
        counter = self.collection.find_one({'_id': self.id})
        counter_val = -2 if counter is None else counter[self.seq_key]
        if counter_val == -2:
            self.collection.insert_one({'_id': self.id, self.seq_key: highest_idx})
            application.logger.info(f"No incremental index data was found for {self.index_dbref}. "
                                    "A new counter has been inserted!")
        elif counter_val < highest_idx:
            self.collection.update_one({'_id': self.id}, {"$set": {self.seq_key: highest_idx}})
            application.logger.warning(f"Incremental index for {self.index_dbref} was outdated. "
                                       "Updated to new unique index value: " + str(highest_idx))

    def get_incremented_index(self, db_session=None):
        # Note that this creates a bottleneck, if there are a huge amount of insert requests incoming.
        # However, this is unproblematic for the labels collection, because there won't be many labels
        result = self.collection.find_one_and_update(self.counter_id, self.incrementer, new=True, session=db_session)
        return result[self.seq_key]

    def multi_increment_index(self, inc_val, db_session=None):
        # retrieves the lowest new index value
        self.multi_incrementer['$inc'][self.seq_key] = inc_val
        result = self.collection.find_one_and_update(self.counter_id, self.multi_incrementer, session=db_session)
        return result[self.seq_key] + 1


class LabelIndexManager(IndexManager):
    def __init__(self):
        super().__init__('labels')


class CorpusIndexManager(IndexManager):
    def __init__(self):
        super().__init__('corpus', 'index')
