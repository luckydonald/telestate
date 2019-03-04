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

### Activate a state
```py
states.STATE_3_A.activate()
```
or
```py
states.set(states.STATE_3_A)
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
