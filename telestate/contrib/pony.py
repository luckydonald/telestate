# -*- coding: utf-8 -*-
from luckydonaldUtils.logger import logging
from pytgbot.api_types.receivable.updates import Update as TGUpdate
from pony import orm

from ..machine import TeleMachine


__author__ = 'luckydonald'

logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logging.add_colored_handler(level=logging.DEBUG)
# end if


class TeleMachinePony(TeleMachine):
    """
     A TeleMachine implementation preserving it's values in a sql instance via PonyORM.
    """

    class State(object):
        """
        Just a fake class proving typing annotations to the StateTable class
        """
        user_id: int
        chat_id: int
        state: str
        data: dict

        def __init__(self):
            raise NotImplementedError(
                "This is only for providing typing annotiations to the IDEs, and shoudn't be used anywhere!")
        # end def
    # end class
    StateTable: State

    def __init__(self, name, db: orm.Database, teleflask_or_tblueprint=None, state_table=None, state_upsert_lock=None):
        """
        A TeleMachine implementation preserving it's values in a sql instance via PonyORM.
        :param name: name of the tblueprint to generate.
        :param db: The database instance to append our tables to.
        :param teleflask_or_tblueprint:
        :param state_table: overwrite the db.State table. If None, the generate one will be accessible at `self.StateTable`.
        :param state_upsert_lock: overwrite the db.StateUpsertLock table. If None, the generate one will be accessible at `self.UpsertLockTable`.
        """
        super().__init__(name, teleflask_or_tblueprint=teleflask_or_tblueprint)

        if state_table is not None:
            assert isinstance(state_table, self.State), "Needs to be subclass of TeleMachinePony.State"
            self.StateTable = state_table
        else:
            class State(db.Entity, self.State):
                user_id = orm.Required(int)
                chat_id = orm.Required(int)
                state = orm.Required(str)
                data = orm.Required(orm.Json)
                orm.PrimaryKey(user_id, chat_id)
            # end class
            self.StateTable = State

        if state_upsert_lock is not None:
            self.UpsertLockTable = state_upsert_lock
        else:
            class StateUpsertLock(db.Entity):
                pass
            # end class
            self.UpsertLockTable = StateUpsertLock
        # end if
    # end def

    @orm.db_session
    def load_state_for_update(self, update):
        chat_id, user_id = self.msg_get_chat_and_user(update)
        state = self.StateTable.get(chat_id=chat_id, user_id=user_id)
        if not state:
            # switch into the default state
            self.set(None, data=None)
            return
        # end if
        self.set(state.state, data=state.data)
        assert self.CURRENT.name == state.state
    # end def

    @orm.db_session
    def save_state_for_update(self, update: TGUpdate):
        chat_id, user_id = self.msg_get_chat_and_user(update)
        state_name = self.CURRENT.name
        state_data = self.CURRENT.data

        excs = []
        ul = self.UpsertLockTable.select().for_update().first()  # enforce only one is in a session.
        for i in range(5):  # limit to 5 tries
            try:  # creating a new state
                self.StateTable(
                    chat_id=chat_id,
                    user_id=user_id,
                    state=state_name,
                    data=state_data,
                )
                break
            except Exception as e:
                excs.append(e)
            # end def
            try:  # updating existing state
                self.StateTable.get(
                    chat_id=chat_id,
                    user_id=user_id
                ).set(
                    chat_id=chat_id,
                    user_id=user_id,
                    state=state_name,
                    data=state_data,
                )
                break
            except Exception as e:
                excs.append(e)
            # end try
        else:
            # we never got successful, never hit a break.
            assert excs, "An error should have occured, as we didn't break."
            raise AssertionError(excs)  # throw them all out
        # end for
    # end def
# end class
