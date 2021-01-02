import pytest
from unittest.mock import Mock, patch

from sync import SyncAirbnb, AirbnbClient
from db import DBDynamo


@pytest.fixture
@patch("db.DBDynamo")
@patch("sync.AirbnbClient")
def sync(AirbnbClient, DBDynamo):
    sync = SyncAirbnb(AirbnbClient(), DBDynamo())
    return sync


@pytest.fixture
def mock_message_one():
    mock = Mock(name="message one")

    mock.message.return_value = "guest message 1"
    mock.sent.return_value = 1000
    mock.user_id.return_value = "002"

    return mock


@pytest.fixture
def mock_message_two():
    mock = Mock(name="message two")

    mock.message.return_value = "host message 1"
    mock.sent.return_value = 1100
    mock.user_id.return_value = "001"

    return mock


@pytest.fixture
def mock_message_three():
    mock = Mock(name="message three")

    mock.message.return_value = "guest message 2"
    mock.sent.return_value = 1100
    mock.user_id.return_value = "002"

    return mock


@pytest.fixture
def mock_message_four():
    mock = Mock(name="message four")

    mock.message.return_value = "guest message 1"
    mock.sent.return_value = 1200
    mock.user_id.return_value = "003"

    return mock


@pytest.fixture
def mock_thread_one_step_one(mock_message_one):
    mock = Mock(name="thread 1 at timestep 1")

    mock.guest_id.return_value = "002"
    mock.updated_at.return_value = 1000
    mock.host_id.return_value = "001"
    mock.messages.return_value = [mock_message_one]
    mock.guest_name.return_value = "Guest 002"

    return mock


@pytest.fixture
def mock_thread_one_step_two(mock_message_one, mock_message_two, mock_message_three):
    mock = Mock(name="thread 1 at timestep 2")

    mock.guest_id.return_value = "002"
    mock.updated_at.return_value = 1100
    mock.host_id.return_value = "001"
    mock.messages.return_value = [
        mock_message_one,
        mock_message_two,
        mock_message_three,
    ]
    mock.guest_name.return_value = "Guest 002"

    return mock


@pytest.fixture
def mock_thread_two_step_three(mock_message_four):
    mock = Mock(name="thread 2 at timestep 3")

    mock.guest_id.return_value = "003"
    mock.updated_at.return_value = 1200
    mock.host_id.return_value = "001"
    mock.messages.return_value = mock_message_four
    mock.guest_name.return_value = "Guest 003"

    return mock


@pytest.fixture
def mock_client(mock_step_one, mock_step_two):
    def side_effect(step):
        vals = {
            1: [mock_thread_one_step_one],
            2: [mock_thread_one_step_two],
            3: [mock_thread_one_step_two, mock_thread_two_step_three],
        }
        return vals[step]

    client = Mock()
    client.get_messages.side_effect = side_effect

    return client


@pytest.fixture
def mock_db_step_zero():
    mock = Mock(name="database at time 0")
    mock.messages_by_host_guest.return_value = []
    mock.guest_by_host.return_value = []

    return mock
