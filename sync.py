from typing import List
import pprint
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
        self.messages = {}
        self.guests = {}
        self.client = client

    def __call__(self, step):
        airbnb_threads = self.client.get_messages(step)
        for thread in airbnb_threads:
            self._update_guest(thread)
            for msg in thread.messages():
                self._update_message(thread.guest_id(), thread.host_id(), msg)

    def _create_message(self, guest_id, host_id, message):
        user = "owner" if message.user_id() == host_id else "guest"
        new_msg = MessageModel(
            guest_id=guest_id,
            user=user,
            message=message.message(),
            channel="airbnb",
            sent=message.sent(),
        )
        self.messages[guest_id].append(new_msg)

    def _create_guest(self, thread):
        guest_id = thread.guest_id()
        new_guest = GuestModel(
            guest_id=guest_id,
            updated_at=thread.updated_at(),
            name=thread.guest_name(),
            total_msgs=len(thread.messages()),
        )
        self.messages[guest_id] = []
        self.guests[guest_id] = new_guest

    def _update_guest(self, thread):
        guest_id = thread.guest_id()

        if guest_id not in self.guests:
            self._create_guest(thread)
            return

        guest = self.guests[guest_id]
        guest.updated_at = thread.updated_at()
        guest.total_msgs = len(thread.messages())

    def _update_message(self, guest_id, host_id, message):
        messages = self.messages[guest_id]

        if not messages:
            self._create_message(guest_id, host_id, message)
            return

        message_ts = [(msg.sent, msg.message) for msg in messages]

        if (message.sent(), message.message()) not in message_ts:
            self._create_message(guest_id, host_id, message)
            messages.sort(key=lambda x: (x.sent, x.message), reverse=True)


sync_1 = SyncAirbnb(AirbnbClient())
sync_1(1)
sync_1(2)

sync_2 = SyncAirbnb(AirbnbClient())
sync_2(2)

assert sync_1.guests == sync_2.guests
assert sync_1.messages == sync_2.messages
