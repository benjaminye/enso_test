from abc import ABC, abstractmethod
from typing import List
import json
import logging

from models import MessageModel, GuestModel, AirbnbThread

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class AirbnbClient:
    """retrieves airbnb threads, do not modify"""

    def __init__(self):
        pass

    def get_messages(self, step=1) -> List[AirbnbThread]:
        assert step in [1, 2]
        with open(f"threads_{step}.json") as file:
            return [AirbnbThread(thread) for thread in json.load(file)]


class SyncAirbnb:
    """syncs airbnb threads with enso database"""

    def __init__(self, client):
        self.db: DBAbstract = DBObject()
        self.client = client

    def __call__(self, step):
        airbnb_threads = self.client.get_messages(step)
        for thread in airbnb_threads:
            self._update_guest(thread)
            for msg in thread.messages():
                self._update_message(thread.guest_id(), thread.host_id(), msg)

    @property
    def messages(self):
        return self.db.messages

    @property
    def guests(self):
        return self.db.guests

    def _create_message(self, guest_id, host_id, message):
        user = "owner" if message.user_id() == host_id else "guest"
        new_msg = MessageModel(
            guest_id=guest_id,
            user=user,
            message=message.message(),
            channel="airbnb",
            sent=message.sent(),
        )
        self.db.add_message(new_msg)

    def _create_guest(self, thread):
        guest_id = thread.guest_id()
        new_guest = GuestModel(
            guest_id=guest_id,
            updated_at=thread.updated_at(),
            name=thread.guest_name(),
            total_msgs=len(thread.messages()),
        )

        self.db.add_guest(new_guest)

    def _update_guest(self, thread):
        guest_id = thread.guest_id()

        if guest_id not in self.guests:
            self._create_guest(thread)
            return

        self.db.update_guest_stat(guest_id, thread.updated_at(), len(thread.messages()))

    def _update_message(self, guest_id, host_id, message):
        messages = self.db.messages_by_guest_id(guest_id)

        if not messages:
            self._create_message(guest_id, host_id, message)
            return

        # I'm using (msg.sent, msg.message) to emulate a hash...
        # ideally we'd implement some sort of hashing algorithm so each message has a unique ID
        messages_hash = [(msg.sent, msg.message) for msg in messages]

        if (message.sent(), message.message()) not in messages_hash:
            self._create_message(guest_id, host_id, message)


class DBAbstract(ABC):
    @property
    @abstractmethod
    def messages(self):
        pass

    @property
    @abstractmethod
    def guests(self):
        pass

    @abstractmethod
    def messages_by_guest_id(self, guest_id: int):
        pass

    @abstractmethod
    def add_guest(self, guest: GuestModel):
        pass

    @abstractmethod
    def add_message(self, message: MessageModel):
        pass

    @abstractmethod
    def update_guest_stat(self, guest_id: int, updated_at: int, total_messages: int):
        pass


class DBObject(DBAbstract):
    def __init__(self):
        self._messages = {}
        self._guests = {}

    @property
    def messages(self):
        messages_sorted = {}
        for guest_id, messages in self._messages.items():
            messages_sorted[guest_id] = self._sort_messages(messages)

        return messages_sorted

    @property
    def guests(self):
        return self._guests

    def messages_by_guest_id(self, guest_id: int):
        messages = self._messages[guest_id]
        return self._sort_messages(messages)

    def add_guest(self, guest: GuestModel):
        guest_id = int(guest.guest_id)
        self._messages[guest_id] = []
        self._guests[guest_id] = guest

    def add_message(self, message):
        guest_id = int(message.guest_id)
        self._messages[guest_id].append(message)

    def update_guest_stat(self, guest_id: int, updated_at: int, total_messages: int):
        guest = self._guests[guest_id]
        guest.updated_at = updated_at
        guest.total_msgs = total_messages

    def _sort_messages(self, messages: List[MessageModel]):
        messages_sorted = sorted(
            messages, key=lambda msg: (msg.sent, msg.message), reverse=True
        )
        return messages_sorted


class DBDynamo(DBAbstract):
    pass


sync_1 = SyncAirbnb(AirbnbClient())
sync_1(1)
sync_1(2)

sync_2 = SyncAirbnb(AirbnbClient())
sync_2(2)

assert sync_1.guests == sync_2.guests
assert sync_1.messages == sync_2.messages
