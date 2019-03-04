# -*- coding: utf-8 -*-
from typing import Tuple, Union

from luckydonaldUtils.logger import logging
from pymongo.collection import Collection
from pytgbot.api_types.receivable.updates import Update as TGUpdate

from .. import TeleMachine


__author__ = 'luckydonald'
__all__ = ['TeleMachineMongo']
logger = logging.getLogger(__name__)


class TeleMachineMongo(TeleMachine):
    """
    A TeleMachine implementation preserving it's values in a mongo db instance.

    It will store im the format of
    ```py
    {
        'chat_id': chat_id,
        'user_id': user_id,
        'state': state_name,
        'data': state_data,
    }
    ```
    Note, if `user_id` or `chat_id` are `None`, that will be stored as `"null"`. See `msg_get_chat_and_user_mongo_prepared(...)`
    """
    def __init__(self, name, mongodb_table, teleflask_or_tblueprint=None):
        assert isinstance(mongodb_table, Collection)
        self.mongodb_table = mongodb_table
        super().__init__(name, teleflask_or_tblueprint)
    # end def

    def load_state_for_update(self, update):
        chat_id, user_id = self.msg_get_chat_and_user_mongo_prepared(update)
        data = self.mongodb_table.find_one(
            filter={'chat_id': chat_id, 'user_id': user_id},
        )
        if not data:
            self.set(None, data=None)
            return
        # end if
        self.set(data['state'], data=data['data'])
        assert self.CURRENT.name == data['state']
    # end def

    def msg_get_chat_and_user_mongo_prepared(
        self, update: TGUpdate
    ) -> Tuple[Union[int, str], Union[int, str]]:
        """
        Like `msg_get_chat_and_user(update)`,
        extracts the chat_id and user_id from an update,
        but replaces `None` with the string `"null"`.

        :param update: The update
        :return: tuple of (chat_id, user_id)
        """
        chat_id, user_id = self.msg_get_chat_and_user(update)
        chat_id = 'null' if chat_id is None else chat_id
        user_id = 'null' if user_id is None else user_id
        return chat_id, user_id
    # end def

    def save_state_for_update(self, update: TGUpdate):
        chat_id, user_id = self.msg_get_chat_and_user_mongo_prepared(update)
        state_name = self.CURRENT.name
        state_data = self.CURRENT.data
        self.mongodb_table.replace_one(
            filter={'chat_id': chat_id, 'user_id': user_id},
            replacement={
                'chat_id': chat_id,
                'user_id': user_id,
                'state': state_name,
                'data': state_data,
            }
        )
    # end def
# end class
