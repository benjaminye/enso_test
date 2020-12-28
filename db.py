from typing import List
from abc import ABC, abstractmethod


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
