# -*- coding: utf-8 -*-
from luckydonaldUtils.logger import logging
from pytgbot.api_types.receivable.updates import Update as TGUpdate

from .. import TeleMachine


__author__ = 'luckydonald'
logger = logging.getLogger(__name__)


class TeleMachineSimpleDict(TeleMachine):
    """
    A TeleMachine implementation preserving it's values in an in-memory python dict.

    Stored like `cache[chat_id][user_id] = (state, data)`:
    ```py
    {
        '1000123123112': {
            '1234': (
                'DEFAULT',
                {'some': 1, 'random': None, 'data': ['yay', 'wooho', 111]}
            )
        },
    }
    """
    def __init__(self, name, teleflask_or_tblueprint=None):
        logger.debug('creating new TeleMachineSimpleDict instance.')
        self.cache = dict()  # {'chat_id': {'user_id': 'state'}}
        super().__init__(name, teleflask_or_tblueprint)
    # end def

    def load_state_for_update(self, update):
        chat_id, user_id = self.msg_get_chat_and_user(update)
        logger.debug('states: {!r}'.format(self.cache))
        cache_data = self.cache.get(chat_id, {})
        # cache_data now contains all the users for the current chat, as dict.
        state_name, cache_data = cache_data.get(user_id, (None, None))
        # cache_data now is the state's data or None,
        # state_name is the state's name or None.
        logger.debug('cached state for {chat_id}|{user_id}: {state_name!r}\ndata: {cache_data!r}')
        if state_name:
            self.set(state_name, data=cache_data)
        else:
            logger.debug('no state found for update.')
            self.set(None, data=None)
        # end def
    # end def

    def save_state_for_update(self, update: TGUpdate):
        chat_id, user_id = self.msg_get_chat_and_user(update)
        state_name = self.CURRENT.name
        data = self.CURRENT.data
        logger.debug(f'storing state for {chat_id}|{user_id}: {state_name!r}\ndata: {data!r}')

        if chat_id not in self.cache:
            # chat_id level does not exist, create, with the {user_id: (state_name, data)} already inserted.
            self.cache[chat_id] = {user_id: (state_name, data)}
        else:
            # chat_id level does exist, just store the state in the user_id dict element. This can overwrite.
            self.cache[chat_id][user_id] = (state_name, data)
        # end if
        logger.debug('states: {!r}'.format(self.cache))
    # end def
# end class
