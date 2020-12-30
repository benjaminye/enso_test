from typing import List, Dict
from abc import ABC, abstractmethod

from models import MessageModel, GuestModel


class DBAbstract(ABC):
    @property
    @abstractmethod
    def messages(self) -> Dict[str, Dict[str, List[MessageModel]]]:
        pass

    @property
    @abstractmethod
    def guests(self) -> Dict[str, Dict[str, GuestModel]]:
        pass

    @abstractmethod
    def messages_by_host(self, host_id: str) -> Dict[str, List[MessageModel]]:
        pass

    @abstractmethod
    def guests_by_host(self, host_id: str) -> Dict[str, GuestModel]:
        pass

    @abstractmethod
    def add_guest(self, host_id: str, guest: GuestModel):
        pass

    @abstractmethod
    def add_message(self, host_id: str, message: MessageModel):
        pass

    @abstractmethod
    def update_guest_stat(
        self, host_id: str, guest_id: str, updated_at: int, total_messages: int
    ):
        pass


class DBObject(DBAbstract):
    def __init__(self):
        self._messages = {}
        self._guests = {}

    @property
    def messages(self):
        messages_sorted = {}
        for host_id, data in self._messages.items():
            messages_sorted[host_id] = {}

            for guest_id, messages in data.items():
                messages_sorted[host_id][guest_id] = self._sort_messages(messages)

        return messages_sorted

    @property
    def guests(self):
        return self._guests

    def messages_by_host(self, host_id: str):
        messages_sorted = {}

        for guest_id, messages in self._messages[host_id].items():
            messages_sorted[guest_id] = self._sort_messages(messages)

        return messages_sorted

    def guests_by_host(self, host_id: str):
        return self._guests[host_id]

    def add_guest(self, host_id: str, guest: GuestModel):
        if host_id not in self._guests:
            self._add_host(host_id)

        guest_id = guest.guest_id
        self._messages[host_id][guest_id] = []
        self._guests[host_id][guest_id] = guest

    def add_message(self, host_id: str, message: MessageModel):
        guest_id = message.guest_id
        self._messages[host_id][guest_id].append(message)

    def update_guest_stat(
        self, host_id: str, guest_id: str, updated_at: int, total_messages: int
    ):
        guest = self._guests[host_id][guest_id]
        guest.updated_at = updated_at
        guest.total_msgs = total_messages

    def _sort_messages(self, messages: List[MessageModel]) -> List[MessageModel]:
        messages_sorted = sorted(
            messages, key=lambda msg: (msg.sent, msg.message), reverse=True
        )
        return messages_sorted

    def _add_host(self, host_id):
        self._messages[host_id] = {}
        self._guests[host_id] = {}


class DBDynamo(DBAbstract):
    pass
