import pytest
from unittest.mock import patch

from sync import SyncAirbnb, AirbnbClient
from models import AirbnbMessage, MessageModel, GuestModel
from db import DBDynamo, DBObject


@pytest.mark.messages
def test_get_all_messages(sync):
    sync.messages()
    sync.db.messages.assert_called_once()


@pytest.mark.guests
def test_get_all_guests(sync):
    sync.guests()
    sync.db.guests.assert_called_once()


@pytest.mark.create_message
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


@pytest.mark.create_message
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


@pytest.mark.create_guest
def test_create_guest(sync, mock_thread_one_step_one):
    expected_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )

    sync._create_guest(mock_thread_one_step_one)

    sync.db.add_guest.assert_called_once_with("001", expected_guest)


@pytest.mark.update_guest
def test_update_guest_read_db(sync, mock_thread_one_step_one):
    sync._update_guest(mock_thread_one_step_one)
    sync.db.guests_by_host.assert_called_once_with("001")


@pytest.mark.update_guest
def test_update_guest_new_guest_empty_db(sync, mock_thread_one_step_one):
    sync.db.guests_by_host.return_value = []
    sync._update_guest(mock_thread_one_step_one)

    expected_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )

    sync.db.add_guest.assert_called_once_with("001", expected_guest)


@pytest.mark.update_guest
def test_update_guest_new_guest(
    sync, mock_thread_one_step_two, mock_thread_two_step_three
):
    existing_guest = GuestModel(
        guest_id=mock_thread_one_step_two.guest_id(),
        updated_at=mock_thread_one_step_two.updated_at(),
        total_msgs=len(mock_thread_one_step_two.messages()),
        name=mock_thread_one_step_two.guest_name(),
    )

    sync.db.guests_by_host.return_value = [existing_guest]

    sync._update_guest(mock_thread_two_step_three)

    expected_guest = GuestModel(
        guest_id=mock_thread_two_step_three.guest_id(),
        updated_at=mock_thread_two_step_three.updated_at(),
        total_msgs=len(mock_thread_two_step_three.messages()),
        name=mock_thread_two_step_three.guest_name(),
    )

    sync.db.add_guest.assert_called_once_with("001", expected_guest)
    assert not (sync.db.update_guest_stat.called)


@pytest.mark.update_guest
def test_update_guest_existing_guest_same_stat(sync, mock_thread_one_step_one):
    existing_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )
    sync.db.guests_by_host.return_value = [existing_guest]
    sync._update_guest(mock_thread_one_step_one)

    assert not (sync.db.add_guest.called)
    assert not (sync.db.update_guest_stat.called)


@pytest.mark.update_guest
def test_update_guest_existing_guest_different_stat(
    sync, mock_thread_one_step_one, mock_thread_one_step_two
):
    existing_guest = GuestModel(
        guest_id=mock_thread_one_step_one.guest_id(),
        updated_at=mock_thread_one_step_one.updated_at(),
        total_msgs=len(mock_thread_one_step_one.messages()),
        name=mock_thread_one_step_one.guest_name(),
    )

    sync.db.guests_by_host.return_value = [existing_guest]
    sync._update_guest(mock_thread_one_step_two)

    expected_args = [
        "001",
        mock_thread_one_step_one.guest_id(),
        mock_thread_one_step_one.updated_at(),
        mock_thread_one_step_two.updated_at(),
        len(mock_thread_one_step_two.messages()),
    ]

    assert not (sync.db.add_guest.called)
    sync.db.update_guest_stat.assert_called_once_with(*expected_args)


@pytest.mark.update_message
def test_update_message_read_db(sync, mock_message_one):
    sync._update_message("002", "001", mock_message_one)
    sync.db.messages_by_host_guest.assert_called_once_with("001", "002")


@pytest.mark.update_message
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


@pytest.mark.update_message
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


@pytest.mark.update_message
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


@pytest.mark.integration
def test_call_step_one_step_two_messages(mock_client):
    # Leveraging Object-based DB that we refactored out from Level-1
    sync_one = SyncAirbnb(mock_client, DBObject())
    sync_one(1)
    sync_one(2)

    sync_two = SyncAirbnb(mock_client, DBObject())
    sync_two(2)

    assert len(sync_one.messages) & len(sync_two.messages)
    assert sync_one.messages == sync_two.messages


@pytest.mark.integration
def test_call_step_one_step_two_guests(mock_client):
    # Leveraging Object-based DB that we refactored out from Level-1
    sync_one = SyncAirbnb(mock_client, DBObject())
    sync_one(1)
    sync_one(2)

    sync_two = SyncAirbnb(mock_client, DBObject())
    sync_two(2)

    assert len(sync_one.guests) & len(sync_two.guests)
    assert sync_one.guests == sync_two.guests


@pytest.mark.integration
def test_call_step_one_step_three_messages(mock_client):
    # Leveraging Object-based DB that we refactored out from Level-1
    sync_one = SyncAirbnb(mock_client, DBObject())
    sync_one(1)
    sync_one(2)
    sync_one(3)

    sync_two = SyncAirbnb(mock_client, DBObject())
    sync_two(3)

    assert len(sync_one.messages) & len(sync_two.messages)
    assert sync_one.messages == sync_two.messages


@pytest.mark.integration
def test_call_step_one_step_three_guests(mock_client):
    # Leveraging Object-based DB that we refactored out from Level-1
    sync_one = SyncAirbnb(mock_client, DBObject())
    sync_one(1)
    sync_one(2)
    sync_one(3)

    sync_two = SyncAirbnb(mock_client, DBObject())
    sync_two(3)

    assert len(sync_one.guests) & len(sync_two.guests)
    assert sync_one.guests == sync_two.guests


@pytest.mark.integration
def test_call_step_two_step_three_messages(mock_client):
    # Leveraging Object-based DB that we refactored out from Level-1
    sync_one = SyncAirbnb(mock_client, DBObject())
    sync_one(2)
    sync_one(3)

    sync_two = SyncAirbnb(mock_client, DBObject())
    sync_two(3)

    assert len(sync_one.messages) & len(sync_two.messages)
    assert sync_one.messages == sync_two.messages


@pytest.mark.integration
def test_call_step_two_step_three_guests(mock_client):
    # Leveraging Object-based DB that we refactored out from Level-1
    sync_one = SyncAirbnb(mock_client, DBObject())
    sync_one(2)
    sync_one(3)

    sync_two = SyncAirbnb(mock_client, DBObject())
    sync_two(3)

    assert len(sync_one.guests) & len(sync_two.guests)
    assert sync_one.guests == sync_two.guests
