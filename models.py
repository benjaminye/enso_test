from pydantic import BaseModel
from typing import Literal
import utils


class AirbnbThread:
    def __init__(self, thread):
        self.thread = thread

    def guest_id(self):
        return self.thread["id"]

    def updated_at(self):
        return utils.parse_timestr(self.thread["last_message_sent_at"])

    def host_id(self):
        return next(
            (
                r["user_ids"][0]
                for r in self.thread["attachment"]["roles"]
                if r["role"] == "owner"
            )
        )

    def messages(self):
        return [AirbnbMessage(m) for m in self.thread["messages"]]

    def guest_name(self):
        return next(
            (u["first_name"] for u in self.thread["users"] if u["id"] != self.host_id())
        )


class AirbnbMessage:
    def __init__(self, message):
        self.msg = message

    def message(self):
        return self.msg["message"]

    def sent(self):
        return utils.parse_timestr(self.msg["created_at"])

    def user_id(self):
        return self.msg["user_id"]


class MessageModel(BaseModel):
    guest_id: str
    sent: int  # milliseconds timestamp
    message: str
    user: Literal["guest", "owner"]
    channel: Literal["airbnb", "SMS", "email", "whatsapp"]


class GuestModel(BaseModel):
    guest_id: str
    updated_at: int  # milliseconds timestamp
    total_msgs: int
    name: str
