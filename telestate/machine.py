# -*- coding: utf-8 -*-
from typing import Dict, cast, Union, Any, Callable, Tuple, Optional

from luckydonaldUtils.exceptions import assert_type_or_raise
from luckydonaldUtils.logger import logging
from luckydonaldUtils.typing import JSONType
from pytgbot.api_types.receivable.updates import Update as TGUpdate
from teleflask import TBlueprint, Teleflask
from teleflask.server.base import TeleflaskMixinBase, TeleflaskBase
from teleflask.server.blueprints import TBlueprintSetupState
from teleflask.server.mixins import StartupMixin

from .state import TeleState, assert_can_be_name, can_be_name

__author__ = 'luckydonald'
__all__ = ["TeleMachine"]


logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logging.add_colored_handler(level=logging.DEBUG)
# end if


class TeleMachine(StartupMixin, TeleflaskMixinBase):
    """
    Statemachine for telegram (flask).
    Basically a TBlueprint, which will select the current state and process only those functions.

    It will load/save the state before/after processing the updates via the functions `load_state_for_chat_user` and `save_state_for_chat_user`.
    Those functions must be implemented via an extending subclass, so you can use different storage backends.

    Usage example:

    >>> states = TeleMachine()  # choose a subclass like `TeleMachineSimpleDict`, see the contrib folder.

    You can access the current state via `states.CURRENT`, and the default state for a new user/chat is `states.DEFAULT`.

    You switch the state with `states.set('EXAMPLE_STATE')`, or `states.EXAMPLE_STATE.activate()`.
    If you want to store additional data, both commands support `data='1234'` parameter.
    That data can be any type, which your storage backend is able to process.
    Using basic python types (`dict`, `list`, `str`, `int`, `bool` and `None`) should be safe to use with most of them.
    """
    def __init__(self, name, teleflask_or_tblueprint=None):
        self.did_init = False
        self.states: Dict[str, TeleState] = {}  # NAME: telestate_instance
        super(TeleMachine, self).__init__()
        if teleflask_or_tblueprint:
            self.blueprint = teleflask_or_tblueprint
            if isinstance(teleflask_or_tblueprint, Teleflask):
                self.is_registered = True
                self.register_bot(teleflask_or_tblueprint)
            # end if
        else:
            self.blueprint = TBlueprint(name)
            self.is_registered = False
        # end def
        if isinstance(teleflask_or_tblueprint, TBlueprint):
            from teleflask.server.blueprints import TBlueprintSetupState
            teleflask_or_tblueprint.record(self.register_bot)
            self.is_registered = teleflask_or_tblueprint._got_registered_once and teleflask_or_tblueprint._teleflask
            self.blueprint.on_startup(self.do_startup)
            self.blueprint.on_update(self.process_update)
        # end if
        self.active_state = None

        self.DEFAULT = TeleState('DEFAULT', self)
        self.ALL = TeleState('ALL', self)  # so you can register to states.ALL to be called on all the states.
        self.CURRENT = self.DEFAULT
        self.did_init = True
    # end def

    def register_bot(self, teleflask_or_tblueprint: Union[TBlueprintSetupState, TBlueprint, Teleflask]):
        """
        Registers an bot to use with the internal blueprint.

        :param tblueprint:
        :type  teleflask_or_tblueprint: Teleflask | TBlueprint
        :return:
        """
        # teleflask_or_tblueprint.register_tblueprint()
        if isinstance(teleflask_or_tblueprint, TBlueprintSetupState):
            teleflask_or_tblueprint = teleflask_or_tblueprint.teleflask
        # end def
        if isinstance(teleflask_or_tblueprint, TBlueprint):
            teleflask_or_tblueprint = teleflask_or_tblueprint.teleflask
        # end def
        for state in self.states.values():
            cast(TeleState, state).register_teleflask(teleflask_or_tblueprint)
        # end def
        if hasattr(self, 'ALL'):
            self.ALL.register_teleflask(teleflask_or_tblueprint)
        # end if
    # end def

    def register_state(self, name, state=None):
        """
        Registers a state.
        Using `self.FOOBAR = state` calls this function with `name=FOOBAR, state=state`
        :param name:
        :param state:
        :return:
        """
        return self._register_state(name, state=state, allow_setting_defaults=not self.did_init)  # prevent setting internal states
    # end def

    def _register_state(self, name, state=None, allow_setting_defaults=False, overwrite=False):
        """
        Registers a state to this TeleMachine.

        :param name: The name of the state we want.
        :type  name: str

        :param state: The state we want to register. If not given, it will be created.
        :type  state: None|TeleState

        :param allow_setting_defaults: if CURRENT and DEFAULT as state name should be allowed. Default: `False`, not allowed.
        :type  allow_setting_defaults: bool

        :param overwrite: if it should overwrite the current set state if already existing.
        :type  overwrite: bool

        :return: If it is valid.
        :rtype:  bool
        :return:
        """
        assert_can_be_name(name, allow_setting_defaults=allow_setting_defaults)
        if name == 'CURRENT':
            # don't overwrite the name when setting as current one.
            logger.debug('changing current.')
            state.register_machine(self)
            object.__setattr__(self, 'CURRENT', state)
        elif name == 'ALL':
            # we don't add this to the states array.
            logger.debug('setting up ALL.')
            if self.did_init or name in self.states:
                raise ValueError('Cant set ALL manually.')
            # end if
            state.register_machine(self)
            if self.is_registered:
                state.register_teleflask(self.teleflask)
            # end if
            object.__setattr__(self, 'ALL', state)
        elif name in self.states:
            logger.debug('adding new, but is existing.')
            if not overwrite:
                raise ValueError('State {name!r} already existing.'.format(name=name))
            # end if
            if state:
                logger.debug('Replacing state {!r} with {!r}.'.format(self.states[name], state))
                state.name = name
                state.register_machine(self, name)
                self.states[name] = state
            else:
                logger.debug('Name given only. Replacing state {!r} with new state.'.format(self.states[name]))
                self.states[name] = TeleState(name, self)
            # end def
            return self.states[name]
        else:
            logger.debug('State {name!r} does not exist. Adding newly.'.format(name=name))
            if not state:  # name given only
                logger.debug('Name given only. Creating new state.')
                state = TeleState(name, self)
            else:  # name + state given
                logger.debug('Registering state.')
                state.register_machine(self, name)
                # end if
            # end if
            self.states[name] = state
            if self.is_registered:
                state.register_teleflask(self.teleflask)
            # end if
        # end if
    # end def

    def __getattr__(self, name):
        logger.debug(name)
        if can_be_name(name) and name in self.states:
            return self.states[name]
        # end if

        # Fallback is normal operation
        object.__getattribute__(self, name)
    # end def

    def __setattr__(self, name, value):
        logger.debug(name)
        if isinstance(value, TeleState):
            assert_can_be_name(name, allow_setting_defaults=not self.did_init)
            self.register_state(name, value)
        # end if

        # Fallback is normal operation
        object.__setattr__(self, name, value)
    # end def

    def __repr__(self):
        return "<{clazz}{states!r}>".format(
            clazz=self.__class__.__name__,
            states=list(self.states.values())
        )
    # end def

    __str__ = __repr__

    def set(self, state: Union[TeleState, str, None], data: Any = None) -> TeleState:
        """
        Sets a state.

        :param state: the new state to set. Can be string or the state object itself.
                      If `None`, the DEFAULT state will be used.

        :param data: additional data to keep for that state

        :return: The new current state, i.e. the one you just applied.
        """
        logger.debug('going to set state {!r}'.format(state))
        logger.debug('got state data: {!r}'.format(data))
        assert_type_or_raise(state, str, TeleState, None, parameter_name='state')
        if isinstance(state, TeleState):
            if state.name not in self.states:
                raise AssertionError(f'next state {state!r} needs to be registered')
            # end if
            if not (state is self.states[state.name]):
                raise AssertionError(f'next state {state!r} is not the registered state {self.states[state.name]!r}')
            # and if
            state = state
        elif isinstance(state, str):
            assert state in self.states, 'state not found'
            state = self.states[state]
        else:  # state == None
            state = self.DEFAULT
        # end if
        self._register_state('CURRENT', state, allow_setting_defaults=True)
        self.CURRENT.set_data(data)
        return self.CURRENT
    # end def

    def process_update(self, update):
        chat_id, user_id = self.msg_get_chat_and_user(update)
        state_name, state_data = self.load_state_for_chat_user(chat_id, user_id)
        if state_name is None:
            state_name = "DEFAULT"
        # end if
        state_data = self.deserialize(state_name, state_data)
        self.set(state_name, data=state_data)
        assert self.CURRENT.name == state_name or (state_name is None and self.CURRENT.name == "DEFAULT")
        current: TeleState = self.CURRENT  # to suppress race-conditions of the logging exception and setting of states.
        logger.debug('Got update for state {}.'.format(current.name))
        # noinspection PyBroadException
        try:
            current.update_handler.process_update(update)
        except:
            logger.exception(f'Update processing for state {current.name} failed.')
        # end try
        # noinspection PyBroadException
        try:
            self.ALL.update_handler.process_update(update)
        except:
            logger.exception('Update processing for special (always active) ALL state failed.')
        # end try
        state_name = self.CURRENT.name
        state_data = self.serialize(state_name, self.CURRENT.data)
        self.save_state_for_chat_user(chat_id, user_id, state_name, state_data)
    # end def

    @property
    def teleflask(self):
        teleflask = self.blueprint
        while isinstance(teleflask, TBlueprint):
            teleflask = teleflask.teleflask
        # end if
        assert isinstance(teleflask, Teleflask)
        return teleflask

    # end def

    @property
    def bot(self):
        """
        Returns the pytgbot Bot instance.
        :return:
        :rtype: pytgbot.bot.Bot
        """
        return self.teleflask.bot
    # end def

    @property
    def username(self):
        return self.teleflask.username
    # end def

    @property
    def user_id(self):
        return self.teleflask.user_id
    # end def

    @staticmethod
    def msg_get_reply_params(update):
        return TeleflaskBase.msg_get_reply_params(update)
    # end def

    def send_messages(self, messages, reply_chat, reply_msg):
        """
        Sends a Message.
        Plain strings will become an unformatted TextMessage.
        Supports to mass send lists, tuples, Iterable.

        :param messages: A Message object.
        :type  messages: Message | str | list | tuple |
        :param reply_chat: chat id
        :type  reply_chat: int
        :param reply_msg: message id
        :type  reply_msg: int
        :param instant: Send without waiting for the plugin's function to be done. True to send as soon as possible.
        False or None to wait until the plugin's function is done and has returned, messages the answers in a bulk.
        :type  instant: bool or None
        """
        return self.teleflask.send_messages(messages, reply_chat, reply_msg)
    # end def

    def process_result(self, update, result):
        """
        Send the result.
        It may be a :class:`Message` or a list of :class:`Message`s
        Strings will be send as :class:`TextMessage`, encoded as raw text.

        :param update: A telegram incoming update
        :type  update: TGUpdate

        :param result: Something to send.
        :type  result: Union[List[Union[Message, str]], Message, str]

        :return: List of telegram responses.
        :rtype: list
        """
        return self.teleflask.process_result(update, result)
    # end def

    @staticmethod
    def msg_get_chat_and_user(update):
        """
        Gets the `chat_id` and `user_id` values from an telegram `pytgbot` `Update` instance.

        :param update: pytgbot.api_types.receivable.updates.Update
        :return: chat_id, user_id
        :rtype: tuple(int,int)
        """
        assert_type_or_raise(update, TGUpdate, parameter_name="update")
        assert isinstance(update, TGUpdate)

        if update.message and update.message.chat.id and update.message.from_peer.id:
            return update.message.chat.id, update.message.from_peer.id
        # end if
        if update.channel_post and update.channel_post.chat.id and update.channel_post.from_peer.id:
            return update.channel_post.chat.id, update.channel_post.from_peer.id
        # end if
        if update.edited_message and update.edited_message.chat.id and update.edited_message.from_peer.id:
            return update.edited_message.chat.id, update.edited_message.from_peer.id
        # end if
        if update.edited_channel_post and update.edited_channel_post.chat.id and update.edited_channel_post.from_peer.id:
            return update.edited_channel_post.chat.id, update.edited_channel_post.from_peer.id
        # end if
        if update.callback_query and update.callback_query.message:
            chat_id = None
            user_id = None

            if update.callback_query.message.chat and update.callback_query.message.chat.id:
                chat_id = update.callback_query.message.chat.id
            # end if
            if update.callback_query.from_peer and update.callback_query.from_peer.id:
                # User who clicked the button
                user_id = update.callback_query.from_peer.id
            elif update.callback_query.message.from_peer and update.callback_query.message.from_peer.id:
                # User who send the message with the keyboard (should be the bot)
                user_id = update.callback_query.message.from_peer.id
            # end if
            return chat_id, user_id
        # end if
        if update.inline_query and update.inline_query.from_peer and update.inline_query.from_peer.id:
            return None, update.inline_query.from_peer.id
        # end if
        logger.debug('Could not find fitting rule for getting user info.')
        return None, None
    # end def

    def load_state_for_chat_user(
        self,
        chat_id: Union[int, str, None],
        user_id: Union[int, str, None]
    ) -> Tuple[Optional[str], JSONType]:
        """
        Loads a state, and sets it.

        :param chat_id: ID of the user/group chat.
        :param user_id: ID of the user.

        :return: Tuple of the name of the state and optionally data.
        """
        raise NotImplementedError('You must implement this in a subclass.')
    # end def

    def save_state_for_chat_user(
        self,
        chat_id: Union[int, str, None],
        user_id: Union[int, str, None],
        state_name: str,
        state_data: JSONType
    ) -> None:
        """
        Saves the current state.

        :param chat_id: ID of the user/group chat.
        :param user_id: ID of the user.
        :param state_name: the name of the current state.
        :param state_data: the additional data for that state.

        :return: Nothing.
        """
        raise NotImplementedError('You must implement this in a subclass.')
    # end def

    # noinspection PyMethodMayBeStatic
    @staticmethod
    def deserialize(state_name, db_data):
        """
        Subclasses can overwrite this function to further process the `data` as loaded from the database,
        e.g. to create classes from it or something.

        :param db_data: The data as it comes from the database. Probably that's a python dict, if you store that.
        :type  db_data: dict | list | int | float | bool | str

        :param state_name: The name of the current state, that's `STATE.data`.
                           This is if you need to have different deserialization for different states.
        :type  state_name: str

        :return: The object you want to interact with when using `STATE.data`.
        :rtype: Any
        """
        return db_data
    # end def

    @staticmethod
    def serialize(state_name, state_data):
        """
        Subclasses can overwrite this function to further get the `STATE.data` to the format we can write it to the database.
        E.g. convert your custom classes back to native python representations (`dict`, `list`, `int`, `float`, `str`, `str`).

        The default implementation just returns it unchanged, and therefore works if you use json-serializable types,
        or whatever your chosen database connector actually requires.

        :param state_data: Basically `STATE.data`, which you can now convert back to something we can store in the database.
        :type  state_data: Any

        :param state_name: The name of the current state, that's `STATE.data`.
                           This is if you need to have different serialization for different states.
        :type  state_name: str

        :return: The native python object which can be written to the database.
        :rtype: dict | list | int | float | bool | str
        """
        return state_data
    # end def
