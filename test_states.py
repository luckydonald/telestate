import unittest, time

from pytgbot.api_types.receivable.media import MessageEntity
from teleflask import Teleflask, TBlueprint
from pytgbot.api_types.receivable.peer import Chat, User
from pytgbot.api_types.receivable.updates import Update, Message
from telestate import TeleState, TeleMachine, state

try:
    from test_data import update1
except ImportError:  # IDE workaround
    from .test_data import update1
# end def


from luckydonaldUtils.logger import logging

logger = logging.getLogger(__name__)
logging.add_colored_handler(level=logging.DEBUG)


class SilentTeleMachine(TeleMachine):
    """
    Don't raise NotImplementedError for load_state_for_update(...) and save_state_for_update(...).
    """

    def load_state_for_update(self, update):
        pass

    # end def

    def save_state_for_update(self, update):
        pass
    # end def


# end class
from pytgbot.bot import Bot


class BotMock(Bot):
    def get_me(self):
        assert self.return_python_objects
        from pytgbot.api_types.receivable.peer import User
        return User(id=0, is_bot=True, first_name="UNITTEST", username="test4458bot")
    # end def


# end def


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.b = Teleflask(
            'FAKE_API_KEY', app=None,
            hostname="localhost",
            debug_routes=False,
            disable_setting_webhook_telegram=True,
            disable_setting_webhook_route=True
        )
        self.m = SilentTeleMachine(__name__, self.b)
        self.s = TeleState('LITTLEPIP')
        self.b._bot = BotMock('FAKE_API_KEY', return_python_objects=True)
        self.b.init_bot()

    # end def

    def test_invalid_name_lowercase(self):
        self.assertFalse(state.can_be_name('penis'))

    # end def

    def test_invalid_name_none(self):
        self.assertFalse(state.can_be_name(''))

    # end def

    def test_invalid_name_special_char_dash(self):
        self.assertFalse(state.can_be_name('FOO-BAR'))

    # end def

    def test_invalid_name_special_char_dot(self):
        self.assertFalse(state.can_be_name('FOO.BAR'))

    # end def

    def test_defaults(self):
        self.assertIsInstance(self.m.DEFAULT, TeleState)
        self.assertEqual(self.m.DEFAULT.name, 'DEFAULT')
        self.assertEqual(self.m.DEFAULT.machine, self.m)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

    # end def

    def test_invalid_state_name(self):
        with self.assertRaises(ValueError) as context:
            s = TeleState('ponies')
        # end def

    # end def

    def test_add_state(self):
        self.assertEqual(self.s.name, 'LITTLEPIP')
        self.m.BEST_PONY = self.s
        self.assertEqual(self.m.BEST_PONY.name, 'BEST_PONY')

    # end def

    def test_switch_state(self):
        self.s = TeleState('LITTLEPIP')
        self.assertEqual(self.s.name, 'LITTLEPIP')
        self.m.BEST_PONY = self.s
        self.assertEqual(self.m.BEST_PONY.name, 'BEST_PONY')
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.CURRENT.name, 'DEFAULT')
        self.m.set(self.s)
        self.assertEqual(self.m.CURRENT, self.s)
        self.assertEqual(self.m.CURRENT.name, 'BEST_PONY')

    # end def

    def test_updates_parent_not_implemented(self):
        update = Update(1)
        m = TeleMachine('a')
        with self.assertRaises(NotImplementedError,
                               msg="should require subclasses to implement load_state_for_update") as context:
            m.load_state_for_update(update)
        # end with

        with self.assertRaises(NotImplementedError,
                               msg="should require subclasses to implement save_state_for_update") as context:
            m.save_state_for_update(update)
        # end with

    # end def

    def test_updates(self):
        self.m.BEST_PONY = self.s
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.CURRENT.name, 'DEFAULT')
        update = Update(1)
        called = [False, False]

        def call_me(i):
            def call_me_inner(u):
                self.assertEqual(u, update)
                called[i] = True

            # end def
            return call_me_inner
        # end def

        self.m.DEFAULT.on_update()(call_me(0))
        self.m.BEST_PONY.on_update()(call_me(1))

        self.m.process_update(update)
        self.assertTrue(called[0], 'DEFAULT should have been called')
        self.assertFalse(called[1], 'BEST_PONY should not have been called')

        called = [False, False]
        self.m.BEST_PONY.activate()
        self.assertEqual(self.m.CURRENT, self.s)
        self.assertEqual(self.m.CURRENT, self.m.BEST_PONY)
        self.assertEqual(self.m.CURRENT.name, 'BEST_PONY')

        self.m.process_update(update)
        self.assertFalse(called[0], 'DEFAULT should not have been called')
        self.assertTrue(called[1], 'BEST_PONY should have been called')

    # end def

    def test_commands(self):
        self.m.BEST_PONY = self.s
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.CURRENT.name, 'DEFAULT')

        update = Update(
            1,
            message=Message(2, date=int(time.time()), chat=Chat(3, 'supergroup', 'FAKE CHAT'), text='/start')
        )
        called = [False, False]

        def call_me(i):
            def call_me_inner(u, text):
                logger.info('called {i}.'.format(i=i))
                self.assertEqual(u, update)
                called[i] = True

            # end def
            return call_me_inner

        # end def

        self.m.DEFAULT.command('start')(call_me(0))
        self.m.BEST_PONY.command('start')(call_me(1))

        self.m.process_update(update)
        self.assertTrue(called[0], 'DEFAULT should have been called')
        self.assertFalse(called[1], 'BEST_PONY should not have been called')

        called = [False, False]
        self.m.BEST_PONY.activate()
        self.assertEqual(self.m.CURRENT, self.s)
        self.assertEqual(self.m.CURRENT, self.m.BEST_PONY)
        self.assertEqual(self.m.CURRENT.name, 'BEST_PONY')

        self.m.process_update(update)
        self.assertFalse(called[0], 'DEFAULT should not have been called')
        self.assertTrue(called[1], 'BEST_PONY should have been called')

    # end def

    def test_data_setter(self):
        test_data = ['something', 'json-ish']
        self.m.CURRENT.set_data(test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)
        self.assertEqual(self.m.DEFAULT.data, test_data)

    # end def

    def test_data_state_activate(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.m.BEST_PONY.activate(test_data)
        self.assertEqual(self.m.BEST_PONY.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_data_statemachine_set(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.m.set('BEST_PONY', data=test_data)
        self.assertEqual(self.m.BEST_PONY.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_data_statemachine_set_new_state(self):
        self.m.register_state('BEST_PONY', self.s)
        test_data = ['something', 'json-ish']
        self.m.set(self.s, data=test_data)
        self.assertEqual(self.m.BEST_PONY.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_data_statemachine_set_new_state_data_in_state_ignored(self):
        self.m.register_state('BEST_PONY', self.s)
        test_data = ['something', 'json-ish']
        self.s = TeleState('LITTLEPIP')
        self.s.set_data(test_data)
        self.assertEqual(self.s.data, test_data, 'we manually set the data')
        self.m.register_state('LITTLEPIP', self.s)
        self.m.set(self.s)
        self.assertEqual(self.m.LITTLEPIP.data, None)
        self.assertEqual(self.m.CURRENT.data, None)

    # end def

    def test_data_statemachine_data_lost_after_switch_activate(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.BEST_PONY.activate()
        self.assertEqual(self.m.CURRENT, self.m.BEST_PONY)
        self.assertEqual(self.m.BEST_PONY.data, None, "never set data for this state")
        self.assertEqual(self.m.CURRENT.data, None, "never set data for this state")

        self.m.DEFAULT.activate()
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

    # end def

    def test_data_statemachine_data_lost_after_switch_set_reference(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.set(self.m.BEST_PONY)
        self.assertEqual(self.m.CURRENT, self.m.BEST_PONY)
        self.assertEqual(self.m.BEST_PONY.data, None, "never set data for this state")
        self.assertEqual(self.m.CURRENT.data, None, "never set data for this state")

        self.m.set(self.m.DEFAULT)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

    # end def

    def test_data_statemachine_data_lost_after_switch_set_str(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.set("BEST_PONY")
        self.assertEqual(self.m.CURRENT, self.m.BEST_PONY)
        self.assertEqual(self.m.BEST_PONY.data, None, "never set data for this state")
        self.assertEqual(self.m.CURRENT.data, None, "never set data for this state")

        self.m.set("DEFAULT")
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

    # end def

    def test_data_statemachine_data_lost_after_switch_activate_self(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.DEFAULT.activate()
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

        self.m.DEFAULT.activate(data=test_data)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_data_statemachine_data_lost_after_switch_set_reference_self(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.set(self.m.DEFAULT)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

        self.m.set(self.m.DEFAULT, data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_data_statemachine_data_lost_after_switch_set_str_self(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.set("DEFAULT")
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

        self.m.set("DEFAULT", data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_data_statemachine_data_lost_after_switch_set_self_None(self):
        self.m.BEST_PONY = self.s
        test_data = ['something', 'json-ish']
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)

        self.m.DEFAULT.set_data(data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

        self.m.set(None)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, None, "should have reset data with None")
        self.assertEqual(self.m.CURRENT.data, None, "should have reset data with None")

        self.m.set(None, data=test_data)
        self.assertEqual(self.m.CURRENT, self.m.DEFAULT)
        self.assertEqual(self.m.DEFAULT.data, test_data)
        self.assertEqual(self.m.CURRENT.data, test_data)

    # end def

    def test_AT_update(self):
        from unittest.mock import MagicMock
        self.m.load_state_for_update: MagicMock = MagicMock(return_value=None)
        self.m.save_state_for_update: MagicMock = MagicMock(return_value=None)

        @self.m.DEFAULT.on_update('message')
        def asdf(update):
            return update

        # end def
        self.m.process_update(update1)
        self.m.load_state_for_update.assert_called_with(update1)
        self.m.save_state_for_update.assert_called_with(update1)
    # end def
# end class


class AnotherTestCase(unittest.TestCase):
    def test_msg_get_chat_and_user_message(self):
        result = TeleMachine.msg_get_chat_and_user(update1)
        self.assertEqual(result, (1234, 4458))
    # end def

    def test_blueprintability(self):
        # test should just not raise any errors.
        states_tbp = TBlueprint(__name__)
        states = SilentTeleMachine(__name__, teleflask_or_tblueprint=states_tbp)

        @states.DEFAULT.command('cancel')
        def func_1(update):
            pass
        # end def

    def test_blueprintability_and_register(self):
        states_tbp = TBlueprint(__name__)
        states: TeleMachine = SilentTeleMachine(__name__, teleflask_or_tblueprint=states_tbp)

        @states.DEFAULT.command('cancel')
        def func_1(update):
            pass
        # end def

        bot = Teleflask(
            'FAKE_API_KEY', app=None,
            hostname="localhost",
            debug_routes=False,
            disable_setting_webhook_telegram=True,
            disable_setting_webhook_route=True
        )
        bot._bot = BotMock('FAKE_API_KEY', return_python_objects=True)
        bot.init_bot()
        bot.register_tblueprint(states_tbp)
        self.assertGreater(len(states.CURRENT.update_handler.commands), 0, 'should have added an command.')
    # end def

    def test_blueprintability_and_execute(self):
        states_tbp = TBlueprint(__name__)
        states = SilentTeleMachine(__name__, teleflask_or_tblueprint=states_tbp)
        called = [False]

        @states.DEFAULT.command('cancel')
        def func_1(update, text):
            called[0] = True
        # end def

        bot = Teleflask(
            'FAKE_API_KEY', app=None,
            hostname="localhost",
            debug_routes=False,
            disable_setting_webhook_telegram=True,
            disable_setting_webhook_route=True
        )
        bot._bot = BotMock('FAKE_API_KEY', return_python_objects=True)
        bot.init_bot()
        bot.register_tblueprint(states_tbp)
        bot.process_update(update1)
        self.assertTrue(called[0], 'func_1 should have been called')
    # end def

    def test_doubleblueprintability_and_execute(self):
        states_tbp = TBlueprint(__name__)
        states_tbp2 = TBlueprint(__name__ + "2")
        states_tbp.register_tblueprint(states_tbp2)
        states = SilentTeleMachine(__name__, teleflask_or_tblueprint=states_tbp2)
        called = [False]

        @states.DEFAULT.command('cancel')
        def func_1(update, text):
            called[0] = True
        # end def

        bot = Teleflask(
            'FAKE_API_KEY', app=None,
            hostname="localhost",
            debug_routes=False,
            disable_setting_webhook_telegram=True,
            disable_setting_webhook_route=True
        )
        bot._bot = BotMock('FAKE_API_KEY', return_python_objects=True)
        bot.init_bot()
        bot.register_tblueprint(states_tbp)
        bot.process_update(update1)
        self.assertTrue(called[0], 'func_1 should have been called')
    # end def
# end class



if __name__ == '__main__':
    unittest.main()
# end if
