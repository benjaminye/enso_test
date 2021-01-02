import pytest
from unittest.mock import patch

from sync import SyncAirbnb, AirbnbClient
from models import AirbnbMessage, MessageModel, GuestModel
from db import DBDynamo


def test_get_all_messages(sync):
    sync.messages()
    sync.db.messages.assert_called_once()


def test_get_all_guests(sync):
    sync.guests()
    sync.db.guests.assert_called_once()


def test_create_message_by_guest(sync, mock_message_one):
    expected_message = MessageModel(
        guest_id="002",
        sent=mock_message_one.sent(),
        message=mock_message_one.message(),
        user="guest",
        channel="airbnb",
    )
    sync._create_message("002", "001", mock_message_one)

    sync.db.add_message.assert_called_once_with("001", expected_message)


def test_create_message_by_host(sync, mock_message_two):
    expected_message = MessageModel(
        guest_id="002",
        sent=mock_message_two.sent(),
        message=mock_message_two.message(),
        user="owner",
        channel="airbnb",
    )

    sync._create_message("002", "001", mock_message_two)

    sync.db.add_message.assert_called_once_with("001", expected_message)


def test_create_guest(sync, mock_thread_one_step_one):
    expected_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )

    sync._create_guest(mock_thread_one_step_one)

    sync.db.add_guest.assert_called_once_with("001", expected_guest)


def test_update_guest_read_db(sync, mock_thread_one_step_one):
    sync._update_guest(mock_thread_one_step_one)
    sync.db.guests_by_host.assert_called_once_with("001")


def test_update_guest_new_guest(sync, mock_thread_one_step_one):
    sync.db.guests_by_host.return_value = []
    sync._update_guest(mock_thread_one_step_one)

    expected_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )

    sync.db.add_guest.assert_called_once_with("001", expected_guest)


@pytest.mark.skip
def test_update_guest_same_guest_db_reads(sync, mock):

    existing_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )

    sync.db.guests_by_host.return_value = [existing_guest]
    sync._update_guest(mock_thread_one_step_one)

    sync.db.guests_by_host.assert_called_once_with("001", expected_guest)


def test_update_message_read_db(sync, mock_message_one):
    sync._update_message("002", "001", mock_message_one)
    sync.db.messages_by_host_guest.assert_called_once_with("001", "002")


def test_update_message_empty_db(sync, mock_message_one):
    sync.db.messages_by_host_guest.return_value = []
    sync._update_message("002", "001", mock_message_one)

    expected_message = MessageModel(
        guest_id="002",
        sent=mock_message_one.sent(),
        message=mock_message_one.message(),
        user="guest",
        channel="airbnb",
    )

    sync.db.add_message.assert_called_once_with("001", expected_message)


def test_update_message_existing_same_message(sync, mock_message_one):
    existing_msg = MessageModel(
        guest_id="002",
        sent=mock_message_one.sent(),
        message=mock_message_one.message(),
        user="guest",
        channel="airbnb",
    )

    sync.db.messages_by_host_guest.return_value = [existing_msg]
    sync._update_message("002", "001", mock_message_one)

    assert not (sync.db.add_message.called)


def test_update_message_existing_different_message(
    sync, mock_message_one, mock_message_two
):
    existing_msg = MessageModel(
        guest_id="002",
        sent=mock_message_one.sent(),
        message=mock_message_one.message(),
        user="guest",
        channel="airbnb",
    )

    sync.db.messages_by_host_guest.return_value = [existing_msg]
    sync._update_message("002", "001", mock_message_two)

    expected_message = MessageModel(
        guest_id="002",
        sent=mock_message_two.sent(),
        message=mock_message_two.message(),
        user="owner",
        channel="airbnb",
    )

    sync.db.add_message.assert_called_once_with("001", expected_message)
