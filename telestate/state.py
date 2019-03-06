# -*- coding: utf-8 -*-
import re
from typing import Any, Union

from luckydonaldUtils.exceptions import assert_type_or_raise
from luckydonaldUtils.logger import logging
from teleflask import TBlueprint, Teleflask
from teleflask.server.base import TeleflaskMixinBase
from teleflask.server.mixins import RegisterBlueprintsMixin, BotCommandsMixin, MessagesMixin, UpdatesMixin


__author__ = 'luckydonald'
__all__ = ["TeleStateUpdateHandler", "TeleState"]


logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logging.add_colored_handler(level=logging.DEBUG)
# end if


_STATE_NAMES_REGEX = '^[A-Z][A-Z0-9_]*$'  # case sensitive


def assert_can_be_name(name, allow_setting_defaults=False):
    """
    Raises an exception if the given string is an invalid state name.
    Uses :py:`TeleMachine.can_be_name` to decide.

    :param name: The name of the state we want.
    :type  name: str

    :param allow_setting_defaults: if CURRENT and DEFAULT should be allowed. Default: `False`, not allowed.
    :type  allow_setting_defaults: bool

    :return: If it is valid.
    :rtype:  bool

    :raises ValueError: Invalid name for a state
    """
    if not can_be_name(name, allow_defaults=allow_setting_defaults):
        raise ValueError(
            'Invalid Name. The state name must be capslock (fully upper case) can only contain numbers and '
            'the underscore.' + ('' if allow_setting_defaults else ' Also DEFAULT and CURRENT are not allowed.')
        )  # also start with an character
    # end if
# end def


def can_be_name(name: str, allow_defaults: bool = False) -> bool:
    """
    Check if a string is valid for usage as state name.

    :param name: The name of the state we want.
    :type  name: str

    :param allow_defaults: if CURRENT and DEFAULT should be allowed. Default: `False`, not allowed.
    :type  allow_defaults: bool

    :return: If it is valid.
    :rtype:  bool
    """
    if not name:
        return False
    # end if
    if not allow_defaults and name in ('CURRENT', 'DEFAULT'):
        return False
    # end if
    if not name.isupper():
        return False
    # end if
    return bool(re.match(_STATE_NAMES_REGEX, name))
# end def


class TeleStateUpdateHandler(RegisterBlueprintsMixin, BotCommandsMixin, MessagesMixin, UpdatesMixin, TeleflaskMixinBase):
    def __init__(self, wrapped_state, teleflask, *args, **kwargs):
        self.wrapped_state: TeleState = wrapped_state
        self.teleflask: Teleflask = teleflask
        super().__init__(*args, **kwargs)
    # end def

    def process_update(self, update):
        """
        This method is called from the flask webserver.

        Any Mixin implementing must call super().process_update(update).
        So catch exceptions in your mixin's code.

        :param update: The Telegram update
        :type  update: pytgbot.api_types.receivable.updates.Update
        :return:
        """
        logger.debug('State {!r} got an update.'.format(self))
        super().process_update(update)
    # end def

    @property
    def username(self):
        return self.wrapped_state.machine.username
    # end def

    @property
    def user_id(self):
        return self.wrapped_state.machine.user_id
    # end def

    def process_result(self, update, result):
        return self.wrapped_state.process_result(update, result)
    # end def
# end class


class TeleState(TBlueprint):
    """
    Basically the TeleState works like a TBlueprint, but is only active when that TeleState is active.
    """
    # :type machine: TeleMachine
    warn_on_modifications = True

    def __init__(self, name=None, machine: 'TeleMachine' = None):
        """
        A new state.

        :param name: Name of the state
        :param data: additional data to keep for that state
        :param machine: Statemachine to register with
        """
        if name:
            assert_can_be_name(name, allow_setting_defaults=True)
        # end if
        from .machine import TeleMachine
        assert_type_or_raise(machine, TeleMachine, None, parameter_name='machine')
        assert machine is None or isinstance(machine, TeleMachine)
        self.machine: TeleMachine = None
        self.data: Any = None
        self.update_handler: Union[None, TeleStateUpdateHandler] = None
        super(TeleState, self).__init__(name)  # writes self.name

        if machine:
            self.register_machine(machine)
        # end def
    # end def

    def register_teleflask(self, teleflask):
        logger.debug(f'Registering update_handler for {self.name!r}: {teleflask!r}')
        if self._got_registered_once:
            logger.warning('already registered')
            return
        # end if
        self.update_handler = TeleStateUpdateHandler(self, teleflask)
        self.update_handler.register_tblueprint(self)
    # end def

    def activate(self, data=None):
        """
        Sets this state as new current step.

        :param data: additional data to store in that state.
        """
        self.machine.set(self, data=data)
    # end def

    def register_machine(self, machine: 'TeleMachine', name=None):
        """
        Registers an bot to use with the internal blueprint.

        :param machine: Instance of the statemachine to register to.
        :type  machine: TeleMachine:
        :param name: Optionally you can overwrite the name.
        :type  name: str
        """
        logger.debug('registering with machine {!r} at name {!r}.'.format(machine, name))
        self.machine = machine
        if name:
            self.name = name
        # end if

    def record(self, func):
        if self.update_handler is None:
            return super().record(func)
        # end def

        # in case we already have update_handler
        logger.warning(f'late addition to {self.name}: {func}')
        state = self.make_setup_state(self.update_handler, {}, first_registration=False)
        func(state)
        # end for
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
        self.machine.process_result(update, result)
    # end def

    def __repr__(self):
        return "<{clazz} {name!r}>".format(
            clazz=self.__class__.__name__,
            name=self.name
        )
    # end def

    __str__ = __repr__

    @property
    def teleflask(self):
        return self.machine.teleflask
    # end def

    @property
    def bot(self):
        """
        Returns the pytgbot Bot instance.
        :return:
        :rtype: pytgbot.bot.Bot
        """
        return self.machine.bot
    # end def

    @property
    def username(self):
        return self.machine.username
    # end def

    @property
    def user_id(self):
        return self.machine.user_id
    # end def

    def set_data(self, data):
        self.data = data
    # end def
# end class
