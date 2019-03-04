# Telestate
A easy to use chat states in telegram, utilizing teleflask.

## Getting started

```py
from telestate import TeleState
from telestate.contrib.simple import TeleMachineSimpleDict
states = TeleMachineSimpleDict(__name__)
```

### Define states
```py
states.STATE_1 = TeleState()
states.STATE_2 = TeleState()
states.STATE_3_A = TeleState()
states.STATE_3_B = TeleState()
```
or
```py
states.register_state('STATE_4', TeleState())
```

### Get current state
The current selected state will be loaded into the magical `CURRENT` state. 
```py
current_state = states.CURRENT
```
Unless you activate a different state,
this will be the automatically existing `DEFAULT` state:
```py
states.CURRENT == state.DEFAULT  # True
states.CURRENT.name == 'DEFAULT'  # True
```

### Activate a state
```py
states.STATE_3_A.activate()
```
or
```py
states.set(states.STATE_3_A)
```

### Additional data for a state
You can supply data to the activate commands.
It will be stored for the current state, and can be used again.

#### Set state data on state switch
All state switching functions have a `data=...` parameter which will accept your data. 
For the in-memory storage that can be any arbitrary data,
for all other storage providers you should only use basic datatypes which safely work with `json.dumps(...)`/`json.loads(...)` (being `bool`, `int`, `float`, `str`, `list`, `dict`).

Also note, if you switch the state, the old state's data will be lost forever. You therefore often want to get the current state and later copy it into the new state.  
```py
states.STATE_3_A.activate(data={'foo': 'bar, 'test': True, 'z0r': 4458})
```
or
```py
states.set(states.STATE_3_A, data="hurr durr")
```
#### Set state data on current state
```py
states.CURRENT.set_data(data=[1234, 'test', 'data'])
```

#### Get current data
```py
data = states.CURRENT.data
```

## Full example
```py
from html import escape

from flask import Flask
from teleflask import Teleflask
from teleflask.messages import HTMLMessage


from telestate import TeleState
from telestate.contrib.simple import TeleMachineSimpleDict

BOT_API_KEY = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'

app = Flask(__name__)
bot = Teleflask(BOT_API_KEY)
states = TeleMachineSimpleDict(__name__, app=app)

states.ASKED_NAME = TeleState()
states.ASKED_AGE = TeleState()
states.CONFIRM_DATA = TeleState()


@bot.command("start")  # command that always works
# @bot.DEFAULT.command("start")  # would only let it work if not already in a different state
def cmd_start(update, text):
    states.ASKED_NAME.activate()
    return "Please tell me your name."
# end def


@bot.command("cancel")
def cmd_cancel(update, text):
    old_action = states.CURRENT 
    states.DEFAULT.activate()
    if old_action == states.DEFAULT:
        return "Nothing to cancel."
    # end if 
    return "All actions canceled."
# end def


@states.ASKED_NAME.on_message("text")
def some_function(update, msg):
    name = msg.text.strip()
    states.ASKED_AGE.activate({"name": name})
    return "Please tell me your age now. If you need to, you can /cancel at any time."
# end def


@states.ASKED_AGE.on_message("text")
def another_function(update, msg):
    name = states.CURRENT.data['name']
    age = msg.text.strip()
    try:
        age = int(age)
    except ValueError:
        # don't change the state
        return "Invalid age, must be an integer. Please tell me your age
    # end try
    states.CONFIRM_DATA.activate({"name": name, "age": age})
    return HTMLMessage(
        f"Is the following correct?\n<b>Name:</b> {escape(name)}\n<b>Age:</b> {age}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Yes', callback_data="confirm_true"),],
            [InlineKeyboardButton('No',  callback_data="confirm_false"),],
        ]),
    )
# end def


@states.CONFIRM_DATA.on_update("callback_query")
def btn_confirm(update):
    if update.callback_query.data != confirm_true:
        states.ASKED_NAME.activate()
        return "Oh, that's bad :(\nWell then. Retry it.\nYour name:"
    # end if
    name=states.CURRENT.data['name']
    age=states.CURRENT.data['age']
    states.DEFAULT.activate()  # we are done
    return HTMLMessage(f"Welcome <i>{escape(name)}</i>!\nHuh, <code>{age}</code> years? Dayum, you are old.")
# end def
```

 
## State storage provider
You can use different storage providers.

They are available at `telestate.contrib.*`:


#### Use in-memory
```py
from telestate import TeleState
from telestate.contrib.simple import TeleMachineSimpleDict
states = TeleMachineSimpleDict(__name__)
```

#### Use MongoDB
```py
from telestate.contrib.mongo import TeleMachineMongo

# change those login information as needed
client = MongoClient("mongodb://username:pa55w0rd@localhost:27017/bot_database")
db = client['bot_database']
states_db = db.states

states = TeleMachineMongo(__name__, mongodb_table=states_db)
```
