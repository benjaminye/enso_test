from typing import List, Dict, Literal
from abc import ABC, abstractmethod
import os

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from models import MessageModel, GuestModel

os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "./credentials"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


class DBAbstract(ABC):
    @property
    @abstractmethod
    def messages(self) -> Dict[str, Dict[str, List[MessageModel]]]:
        """
        Returns all messages stored within Database
        """
        pass

    @property
    @abstractmethod
    def guests(self) -> Dict[str, Dict[str, GuestModel]]:
        """
        Returns all guests stored within Database
        """
        pass

    @abstractmethod
    def messages_by_host_guest(self, host_id: str, guest_id: str) -> List[MessageModel]:
        """
        Returns all messages sent between a specific host and guest
        """
        # TODO: Can implement some sort of timed lru chaching to reduce DB reads
        pass

    @abstractmethod
    def guests_by_host(self, host_id: str) -> List[GuestModel]:
        """
        Returns all guests of a specific host
        """
        # TODO: Can implement some sort of timed lru chaching to reduce DB reads
        pass

    @abstractmethod
    def add_guest(self, host_id: str, guest: GuestModel):
        """
        Add a guest into database
        """
        pass

    @abstractmethod
    def add_message(self, host_id: str, message: MessageModel):
        """
        Add a message into database
        """
        pass

    @abstractmethod
    def update_guest_stat(
        self,
        host_id: str,
        guest_id: str,
        old_updated_at: int,
        new_updated_at: int,
        new_total_messages: int,
    ):
        """
        Update updated_at and total_msgs stats of an existing guest thread
        """
        pass


class DBObject(DBAbstract):
    """
    Implementation of database using object
    """

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

    def messages_by_host_guest(self, host_id: str, guest_id: str):
        messages = self._messages.get(host_id).get(guest_id)

        return self._sort_messages(messages)

    def guests_by_host(self, host_id: str):
        guests_sorted = []

        guests = self._guests.get(host_id)

        if not guests:
            return guests_sorted

        for guest in guests.values():
            guests_sorted.append(guest)

        return sorted(guests_sorted, key=lambda guest: guest.updated_at, reverse=True)

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
        self,
        host_id: str,
        guest_id: str,
        old_updated_at: int,
        new_updated_at: int,
        new_total_messages: int,
    ):
        guest = self._guests[host_id][guest_id]
        guest.updated_at = new_updated_at
        guest.total_msgs = new_total_messages

    def _sort_messages(self, messages: List[MessageModel]):
        messages_sorted = sorted(
            messages, key=lambda msg: (msg.sent, msg.message), reverse=True
        )
        return messages_sorted

    def _add_host(self, host_id):
        self._messages[host_id] = {}
        self._guests[host_id] = {}


class DBDynamo(DBAbstract):
    """
    Implementation of database using DynamoDB
    """

    def __init__(self, table_name):
        try:
            # connect to an existing DynamoDB with specified name
            self.table = self._connect_table(table_name)
        except ClientError:
            # if doesn't exist, create one with the correct spec
            self.table = self._create_table(table_name)

    @property
    def messages(self):
        result = {}

        data = self._query_table("msg")
        data = [(MessageModel(**item["itemData"]), item["itemID"]) for item in data]

        for message, key in data:
            host_id, guest_id, *_ = key.split("#")

            if host_id not in result:
                result[host_id] = {}

            if guest_id not in result[host_id]:
                result[host_id][guest_id] = []

            result[host_id][guest_id].append(message)

        return result

    @property
    def guests(self):
        result = {}

        data = self._query_table("guest")
        data = [(GuestModel(**item["itemData"]), item["itemID"]) for item in data]

        for guest, key in data:
            host_id, _, guest_id = key.split("#")

            if host_id not in result:
                result[host_id] = {}

            result[host_id][guest_id] = guest

        return result

    def messages_by_host_guest(self, host_id: str, guest_id: str):
        data = self._query_table("msg", f"{host_id}#{guest_id}", ["itemData"])
        data = [item["itemData"] for item in data]
        data = [MessageModel(**message) for message in data]

        return data

    def guests_by_host(self, host_id: str):
        data = self._query_table("guest", get_attributes=["itemData"])
        data = [item["itemData"] for item in data]
        data = [GuestModel(**guest) for guest in data]

        return data

    def add_guest(self, host_id: str, guest: GuestModel):
        updated_at, guest_id = guest.updated_at, guest.guest_id
        key = "#".join([host_id, str(updated_at), guest_id])

        self.table.put_item(
            Item={
                "itemType": "guest",
                "itemID": key,
                "itemData": guest.dict(),
            }
        )

    def add_message(self, host_id: str, message: MessageModel):
        guest_id, sent = message.guest_id, message.sent

        data = self._query_table("msg", f"{host_id}#{guest_id}#{sent}", ["itemData"])
        suffix = len(data)

        key = "#".join([host_id, guest_id, str(sent), str(suffix)])

        self.table.put_item(
            Item={
                "itemType": "msg",
                "itemID": key,
                "itemData": message.dict(),
            }
        )

    def update_guest_stat(
        self,
        host_id: str,
        guest_id: str,
        old_updated_at: int,
        new_updated_at: int,
        new_total_messages: int,
    ):
        # find old record
        old_key = {
            "Key": {
                "itemType": "guest",
                "itemID": "#".join([host_id, str(old_updated_at), guest_id]),
            }
        }

        old_guest = self.table.get_item(**old_key)["Item"]["itemData"]

        # delete old record
        self.table.delete_item(Key={"itemType": "guest", "itemID": old_key})

        # update stat
        new_guest = GuestModel(**old_guest)
        new_guest.updated_at = new_updated_at
        new_guest.total_msgs = new_total_messages

        # add new record
        self.table.put_item(
            Item={
                "itemType": "guest",
                "itemID": "#".join([host_id, str(new_updated_at), guest_id]),
                "itemData": new_guest.dict(),
            }
        )

    def _query_table(
        self,
        partition_key: Literal["guest", "msg"],
        sort_key: str = None,
        get_attributes: list = None,
        filter_exp: Attr = None,
    ):
        query_parameters = {
            "KeyConditionExpression": Key("itemType").eq(partition_key),
            "ScanIndexForward": False,
        }

        if sort_key:
            query_parameters.update(
                {
                    "KeyConditionExpression": Key("itemType").eq(partition_key)
                    & Key("itemID").begins_with(sort_key)
                }
            )

        if get_attributes:
            query_parameters.update({"ProjectionExpression": ",".join(get_attributes)})

        if filter_exp:
            query_parameters.update({"FilterExpression": filter_exp})

        response = self.table.query(**query_parameters)
        data = response["Items"]

        # append data if response is paginated
        while "LastEvaluatedKey" in response:
            response = self.table.query(ExclusiveStartKey=response["LastEvaluatedKey"])
            data.extend(response["Items"])

        return data

    def _create_table(self, table_name):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "itemType", "KeyType": "HASH"},
                {"AttributeName": "itemID", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "itemType", "AttributeType": "S"},
                {"AttributeName": "itemID", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)

        return table

    def _connect_table(self, table_name: str):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        return table
