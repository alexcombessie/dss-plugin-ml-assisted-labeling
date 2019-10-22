import dataiku
from datetime import datetime
import logging
from base64 import b64encode

from lal.base_classifier import BaseClassifier


class ImageClassifier(BaseClassifier):
    logger = logging.getLogger(__name__)

    def __init__(self):
        super(ImageClassifier, self).__init__()
        self.folder = dataiku.Folder(self.config["folder"])
        self.queries_ds = dataiku.Dataset(self.config["queries_ds"])
        self.current_user = dataiku.api_client().get_auth_info()['authIdentifier']

    def add_annotation(self, annotaion):
        sid = annotaion.get('sid')
        cat = annotaion.get('category')
        # comment = annotaion.get('comment')
        comment = annotaion.get('points')

        self.annotations_df = self.annotations_df.append({
            'date': datetime.now(),
            'id': sid,
            'class': cat,
            'comment': comment,
            'session': 0,
            'annotator': self.current_user,
        }, ignore_index=True)

    @property
    def annotations_required_schema(self):
        # TODO: Named tuple?
        return [
            {"name": "date", "type": "date"},
            {"name": "id", "type": "string"},
            {"name": "class", "type": "string"},
            {"name": "comment", "type": "string"},
            {"name": "session", "type": "int"},
            {"name": "annotator", "type": "string"}]

    def get_sample_by_id(self, sid):
        self.logger.info('Reading image from: ' + str(sid))
        with self.folder.get_download_stream(sid) as s:
            data = b64encode(s.read())

        self.logger.info("Read: {0}, {1}".format(len(data), type(data)))
        return data.decode('utf-8')

    def get_all_sample_ids(self):
        self.logger.info("Reading queries_ds")
        try:
            self.logger.info(self.queries_ds.get_dataframe()['id'].shape)
            return set(self.queries_ds.get_dataframe()['id'].tolist())
        except:
            self.logger.info("Couldn't read queries_ds")
            return set(self.folder.list_paths_in_partition())

    def get_labeled_sample_ids(self):
        return set(self.annotations_df.loc[self.annotations_df['annotator'] == self.current_user]['id'])