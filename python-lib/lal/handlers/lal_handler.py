import hashlib
import json
import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from threading import RLock
from typing import TypeVar, Dict

import pandas as pd

from lal.classifiers.base_classifier import BaseClassifier

logging.basicConfig(level=logging.INFO, format='%(name)s %(levelname)s - %(message)s')

META_STATUS_LABELED = 'LABELED'
META_STATUS_SKIPPED = 'SKIPPED'

BLOCK_SAMPLE_BY_USER_FOR_MINUTES = 0.5
BATCH_SIZE = 20

C = TypeVar('C', bound=BaseClassifier)


class ReservedSample:
    username: str
    reserved_until: datetime

    def __init__(self, username: str, reserved_until: datetime) -> None:
        self.username = username
        self.reserved_until = reserved_until

    def __repr__(self) -> str:
        return f"User: {self.username}; Reserved until: {self.reserved_until}"


class LALHandler(object):
    lock = RLock()
    sample_by_user_reservation: Dict[str, ReservedSample] = dict()
    logger = logging.getLogger(__name__)

    def __init__(self, classifier, label_col_name, meta_df, labels_df, user, do_users_share_labels=True):
        """
        :type classifier: C
        """
        self.classifier = classifier
        self.lbl_col = label_col_name
        self.lbl_id_col = label_col_name + "_id"
        self._skipped = {}
        self.meta_df = meta_df
        self.labels_df = labels_df
        self.current_user = user
        self.do_users_share_labels = do_users_share_labels

    def get_meta_by_status(self, status=None):
        if self.do_users_share_labels:
            return self.meta_df if status is None else self.meta_df[self.meta_df.status == status]
        else:
            if status is None:
                return self.meta_df[self.meta_df.annotator == self.current_user]
            return self.meta_df[
                (self.meta_df.status == status) & (self.meta_df.annotator == self.current_user)]

    def get_remaining(self):
        labeled_ids = set(self.get_meta_by_status().data_id.values)
        logging.info("get_remaining: Seen ids: {0}".format(labeled_ids))
        unlabeled_ids = [i for i in self.classifier.get_all_item_ids_list() if i not in labeled_ids]
        result = []
        with LALHandler.lock:
            for i in unlabeled_ids:
                if i in self.sample_by_user_reservation:
                    reserved_sample = self.sample_by_user_reservation.get(i)
                    if reserved_sample.reserved_until <= datetime.now():
                        del self.sample_by_user_reservation[i]
                    else:
                        if reserved_sample.username == self.current_user:
                            result.append(i)
                else:
                    result.append(i)
        return result

    def calculate_stats(self):
        total_count = len(self.classifier.get_all_item_ids_list())
        stats = {
            "labeled": len(self.get_meta_by_status(META_STATUS_LABELED)),
            "total": total_count,
            "skipped": len(self.get_meta_by_status(META_STATUS_SKIPPED)),
            "perLabel": self.get_meta_by_status(META_STATUS_LABELED)[self.lbl_col].astype(
                'str').value_counts().to_dict()
        }
        return stats

    def get_config(self):
        result = {"al_enabled": self.classifier.is_al_enabled}
        custom_config = self.classifier.get_config()
        if custom_config is not None:
            result = {**result, **custom_config}
        return result

    def label(self, data):
        self.logger.info("Labeling: %s" % json.dumps(data))
        if 'id' not in data:
            message = "Labeling data doesn't contain sample ID"
            self.logger.error(message)
            raise ValueError(message)

        data_id = data.get('id')
        lbl_id = self.create_label_id(data_id)
        raw_data = self.classifier.get_raw_item_by_id(data_id)

        serialized_label = self.classifier.serialize_label(data.get('label'))
        label = {**raw_data, **{self.lbl_col: serialized_label, self.lbl_id_col: lbl_id}}
        meta = {
            'date': datetime.now(),
            'data_id': data_id,
            'status': META_STATUS_LABELED,
            self.lbl_col: serialized_label,
            self.lbl_id_col: lbl_id,
            'comment': data.get('comment'),
            'session': self.classifier.get_session(),
            'annotator': self.current_user,
        }
        self.meta_df = self.meta_df[self.meta_df[self.lbl_id_col] != lbl_id]
        self.meta_df = self.meta_df.append(meta, ignore_index=True)

        self.labels_df = self.labels_df[self.labels_df[self.lbl_id_col] != lbl_id]
        self.labels_df = self.labels_df.append(label, ignore_index=True)

        self.save_item_label(self.labels_df, label)
        self.save_item_meta(self.meta_df, meta)
        return {
            "label_id": lbl_id,
            "stats": self.calculate_stats()
        }

    def create_label_id(self, data_id):
        return hashlib.md5(''.join([str(data_id), self.current_user]).encode('utf-8')).hexdigest()

    def is_stopping_criteria_met(self):
        return len(self.get_remaining()) < 0

    def get_batch(self):
        self.logger.info("Getting unlabeled batch")
        stats = self.calculate_stats()
        self.logger.info("Stats: {0}".format(stats))
        if self.is_stopping_criteria_met():
            return {"isDone": True, "stats": stats}

        remaining = self.get_remaining()
        ids_batch = remaining[-BATCH_SIZE:]
        with LALHandler.lock:
            for i in ids_batch:
                if i not in self.sample_by_user_reservation:
                    reserved_until = datetime.now() + timedelta(minutes=int(BATCH_SIZE * BLOCK_SAMPLE_BY_USER_FOR_MINUTES))
                    self.sample_by_user_reservation[i] = ReservedSample(self.current_user, reserved_until)
        ids_batch.reverse()
        return {
            "type": self.classifier.type,
            "items": [{"id": data_id, "data": self.classifier.get_item_by_id(data_id)} for data_id in ids_batch],
            "isLastBatch": len(remaining) < BATCH_SIZE,
            "stats": stats
        }

    def current_user_meta(self):
        return self.meta_df[(self.meta_df.annotator == self.current_user)]

    def back(self, current_data_id):
        self.logger.info(f"Going back from {current_data_id}")
        meta = self.current_user_meta()

        current_data_meta = meta[meta['data_id'] == current_data_id]
        if len(current_data_meta):
            meta = meta[meta.date < current_data_meta.iloc[0].date]
            previous = meta.sort_values(by='date', ascending=False)
            previous = previous.iloc[0] if len(previous) else None
        else:
            previous = meta.sort_values(by='date', ascending=False).iloc[0]

        previous = previous.where((pd.notnull(previous)), None).astype('object').to_dict()
        data_id = previous['data_id']

        if previous['status'] != META_STATUS_SKIPPED:
            label = self.classifier.deserialize_label(previous[self.lbl_col])
        else:
            label = None
        return {
            "annotation": {"label": label, "comment": previous['comment']},
            "isFirst": len(meta) == 1,
            "item": {"id": data_id,
                     "labelId": previous[self.lbl_id_col],
                     "data": self.classifier.get_item_by_id(data_id)}
        }

    def skip(self, data):
        data_id = data.get('dataId')
        label_id = data.get('labelId')
        lbl_id = self.create_label_id(data_id)
        meta = {
            'date': datetime.now(),
            'data_id': data_id,
            'status': META_STATUS_SKIPPED,
            self.lbl_col: None,
            self.lbl_id_col: lbl_id,
            'comment': data.get('comment'),
            'session': self.classifier.get_session(),
            'annotator': self.current_user,
        }
        self.meta_df = self.meta_df[self.meta_df[self.lbl_id_col] != lbl_id]
        self.meta_df = self.meta_df.append(meta, ignore_index=True)

        if label_id:
            self.labels_df = self.labels_df[self.labels_df[self.lbl_id_col] != lbl_id]

        self.save_item_meta(self.meta_df, meta)
        self.save_item_label(self.labels_df)
        return {"label_id": lbl_id, "stats": self.calculate_stats()}

    @abstractmethod
    def save_item_label(self, new_label_df, new_label=None):
        pass

    @abstractmethod
    def save_item_meta(self, new_meta_df, new_meta=None):
        pass
