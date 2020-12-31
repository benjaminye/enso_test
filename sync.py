from typing import List
import json
import logging

from models import MessageModel, GuestModel, AirbnbThread
from db import DBAbstract, DBObject, DBDynamo

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

    def __init__(self, client, db: DBAbstract):
        self.db = db
        self.client = client

    def __call__(self, step):
        airbnb_threads = self.client.get_messages(step)
        for thread in airbnb_threads:
            self._update_guest(thread)
            for msg in thread.messages():
                self._update_message(str(thread.guest_id()), str(thread.host_id()), msg)

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
        self.db.add_message(host_id, new_msg)

    def _create_guest(self, thread):
        guest_id = str(thread.guest_id())
        host_id = str(thread.host_id())

        new_guest = GuestModel(
            guest_id=guest_id,
            updated_at=thread.updated_at(),
            name=thread.guest_name(),
            total_msgs=len(thread.messages()),
        )

        self.db.add_guest(host_id, new_guest)

    def _update_guest(self, thread):
        guest_id = str(thread.guest_id())
        host_id = str(thread.host_id())

        # Case 1: new guest
        if guest_id not in self.db.guests_by_host(host_id):
            self._create_guest(thread)
            return

        # Case 2: existing guest
        guest = self.db.guests_by_host(host_id)[guest_id]
        if thread.updated_at() != guest.updated_at:
            self.db.update_guest_stat(
                host_id,
                guest_id,
                guest.updated_at,
                thread.updated_at(),
                len(thread.messages()),
            )

    def _update_message(self, guest_id, host_id, message):
        messages = self.db.messages_by_host_guest(host_id, guest_id)

        if not messages:
            self._create_message(guest_id, host_id, message)
            return

        # I'm using (msg.sent, msg.message) to emulate a hash...
        # ideally we'd implement some sort of hashing algorithm server-side so each message is uniquely identifiable
        messages_hash = [(msg.sent, msg.message) for msg in messages]
        current_hash = (message.sent(), message.message())

        if current_hash not in messages_hash:
            self._create_message(guest_id, host_id, message)
