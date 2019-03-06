# -*- coding: utf-8 -*-
from luckydonaldUtils.logger import logging
from pytgbot.api_types.receivable.peer import Chat, User
from pytgbot.api_types.receivable.updates import Update, Message

__author__ = 'luckydonald'

logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logging.add_colored_handler(level=logging.DEBUG)
# end if


update1 = Update(
    update_id=0,
    message=Message(
        message_id=0,
        date=0,
        chat=Chat(
            id=1234,
            type='private'
        ),
        from_peer=User(
            id=4458,
            is_bot=False,
            first_name="user",
            last_name="test"
        ),
        text="/cancel"
    )
)

update2 = Update.from_array({
    "message": {
        "chat": {
            "first_name": "luckydonald",
            "id": 10717954,
            "last_name": "‎",
            "type": "private",
            "username": "luckydonald"
        },
        "date": 1551809908,
        "entities": [
            {
                "length": 19,
                "offset": 0,
                "type": "bot_command"
            }
        ],
        "from": {
            "first_name": "luckydonald",
            "id": 10717954,
            "is_bot": False,
            "language_code": "en",
            "last_name": "‎",
            "username": "luckydonald"
        },
        "message_id": 409,
        "text": "/start@teleflaskBot test"
    },
    "update_id": 57913582
})
