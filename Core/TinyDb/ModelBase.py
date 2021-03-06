from abc import ABC
from collections.abc import Mapping
from datetime import datetime

from skpy import SkypeUser, SkypeChat
from tinydb.database import Document


class ModelBase(Mapping, ABC):
    def __getitem__(self, k):
        return self.__serializer_dict().__getitem__(k)

    def __iter__(self):
        return self.__serializer_dict().__iter__()

    def __len__(self):
        return self.__serializer_dict().__len__()

    def __serializer_dict(self) -> dict:
        all_properties = dict(self.__dict__)
        if 'doc_id' in all_properties:
            del all_properties['doc_id']
        return all_properties

    def __init__(self):
        super(ModelBase, self).__init__()

        self.doc_id = None
        self.chat_id = None
        self.created_at = datetime.now()
        self.user_id = None
        self.user_name = None

    def with_context(self, user: SkypeUser, chat: SkypeChat):
        self.chat_id = chat.id
        self.user_id = user.id
        self.user_name = user.name
        return self

    def fill(self, doc: Document):
        self.doc_id = doc.doc_id
        self.chat_id = doc['chat_id']
        self.created_at = doc['created_at']
        self.user_id = doc['user_id']
        self.user_name = doc['user_name']
        return self
