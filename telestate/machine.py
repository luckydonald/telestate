# -*- coding: utf-8 -*-
import re
from typing import Dict, cast, Union, Any

from luckydonaldUtils.exceptions import assert_type_or_raise
from luckydonaldUtils.logger import logging
from pytgbot.api_types.receivable.updates import Update as TGUpdate
from teleflask import TBlueprint, Teleflask
from teleflask.server.base import TeleflaskMixinBase, TeleflaskBase
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

    It will load/save the state before/after processing the updates via the functions `load_state_for_update` and `save_state_for_update`.
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
        super(TeleMachine, self).__init__()
        if teleflask_or_tblueprint:
            self.blueprint = teleflask_or_tblueprint
        else:
            self.blueprint = TBlueprint(name)
            self.is_registered = False
        # end def
        self.blueprint.on_startup(self.do_startup)
        self.blueprint.on_update(self.process_update)
        self.states: Dict[str, TeleState] = {}  # NAME: telestate_instance
        self.register_bot()
        self.active_state = None

        self.DEFAULT = TeleState('DEFAULT', self)
        self.CURRENT = self.DEFAULT
        self.did_init = True
    # end def

    def register_bot(self):
        """
        Registers an bot to use with the internal blueprint.

        :param teleflask_or_tblueprint:
        :type  teleflask_or_tblueprint: Teleflask | TBlueprint
        :return:
        """
        # teleflask_or_tblueprint.register_tblueprint()
        for state in self.states.values():
            cast(TeleState, state).register_handler()
        # end def
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

    def _register_state(self, name, state=None, allow_setting_defaults=False):
        """
        Registers a state to this TeleMachine.

        :param name: The name of the state we want.
        :type  name: str

        :param state: The state we want to register. If not given, it will be created.
        :type  state: None|TeleState

        :param data: Additional data to

        :param allow_setting_defaults: if CURRENT and DEFAULT as state name should be allowed. Default: `False`, not allowed.
        :type  allow_setting_defaults: bool

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
        elif name in self.states:
            logger.debug('adding new, but is existing.')
            raise ValueError('State {name!r} already existing.'.format(name=name))
            # TODO:
            if state:
                logger.debug('Replacing state {!r} with {!r}.'.format(self.states[name], state))
                state.name = name
                self.states[name] = state
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
            state.register_handler()
            self.states[name] = state
        # end if
    # end def

    def __getattr__(self, name):
        logger.debug(name)
        if can_be_name(name):
            if name in self.states:
                return self.states[name]
            # end if
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
        self.load_state_for_update(update)
        current: TeleState = self.CURRENT  # to suppress race-conditions of the logging exception and possible setting of states.
        logger.debug('Got update for state {}.'.format(current.name))
        # TODO: load state here
        # noinspection PyBroadException
        try:
            current.update_handler.process_update(update)
            self.save_state_for_update(update)
        except:
            logger.exception('Sate update processing for state {} failed.'.format(current.name))
        # end def
    # end def

    @property
    def teleflask(self):
        if isinstance(self.blueprint, Teleflask):
            return self.blueprint
        # end if
        return self.blueprint.teleflask
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
            if update.callback_query.message.from_peer and update.callback_query.message.from_peer.id:
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

    def load_state_for_update(self, update: TGUpdate):
        """
        Loads a state, and sets it.

        :param update: The update, to get information about chat and user ids.
        :return: Nothing.
        """
        raise NotImplementedError('You must implement this in a subcclass.')
    # end def

    def save_state_for_update(self, update: TGUpdate):
        """
        Saves the current state.

        :param update: The update, to get information about chat and user ids.
        :return: Nothing.
        """
        raise NotImplementedError('You must implement this in a subcclass.')
    # end def