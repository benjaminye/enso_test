## Enso Connect onboarding challenge

One of enso's key features is our unified inbox, which combines messages across email, SMS, airbnb &whatsapp. For this challenge, you are tasked with "integrating" our messages & guest database with Airbnb's messaging API.

### Given
* Your are given a minimal version of our `SyncAirbnb` class, whose job is it to pull in airbnb threads and sync them up with our messages and guests database. This minimal version uses two internal attributes `self.messages` and `self.guests` as its "database", and only creates new message threads/guests. Run `python sync.py` to test this.
```python
class SyncAirbnb:
	"""syncs airbnb threads with enso database"""
	def __init__(self, client):
		self.messages = {}
		self.guests = {}
		self.client = client

	def __call__(self, step):
		airbnb_threads = self.client.get_messages(step)
		for thread in airbnb_threads:
			self._create_guest(thread)
			for msg in thread.messages():
				self._create_message(thread.guest_id(), 
									 thread.host_id(), msg)


	def _create_message(self, guest_id, host_id, message):
		user = 'owner' if message.user_id() == host_id else 'guest'
		new_msg = MessageModel(
			guest_id=guest_id,
			user=user,
			message=message.message(),
			channel='airbnb',
			sent=message.sent()
		)
		self.messages[guest_id].append(new_msg)

	def _create_guest(self, thread):
		guest_id = thread.guest_id()
		new_guest = GuestModel(
			guest_id=guest_id,
			updated_at=thread.updated_at(),
			name=thread.guest_name(),
			total_msgs=len(thread.messages())
		)
		self.messages[guest_id] = []
		self.guests[guest_id] = new_guest
```

* You are also given a mock version of the the airbnb API client, which returns an array of airbnb threads at different time steps. Each thread corresponds to a conversation with a guest (just like in any messenger application) and contains an array of messages. Make any assumptions you need to about the schema of each thread.
 ```python
class AirbnbClient:
	def __init__(self):  
		pass
		
	def get_messages(self, step=1): 
		assert step in [1,2]
		with open(f'threads_{step}.json') as file:
		  return [AirbnbThread(thread) for thread in json.load(file)]
```
* You are also given the models of our guest/message objects.
```python
class MessageModel(BaseModel):
	guest_id: str
	sent: int # milliseconds timestamp
	message: str
	user: Literal['guest', 'owner']
	channel: Literal['airbnb','SMS','email','whatsapp']


class GuestModel(BaseModel):
	guest_id: str
	updated_at: int # milliseconds timestamp
	total_msgs: int
	name: str
```

NOTE: This code is already in the files provided. no need to copy/paste.

### Challenge Specs
You will be completeing the polling function, `SyncAirbnb`, that synchronizes the airbnb threads with our internal store of messages.

Complete as many levels as you can.

* Level 1: Modify SyncAirbnb to synchronize the messages at the second timestep. At the first timestep, all threads & messages are new, so you only need create methods. However, at the second timestep, the threads are already synced, so you will need to compare with the SyncAirbnb database to only push in messages that were not present in timestep 1.

* Level 2: Modify `SyncAirbnb` to save & query to a dynamoDB table, replacing `self.messages` and `self.guests` as your database. You will need an AWS account & boto3 configured on your machine for this. Choose your sort keys wisely! (Hint: think of how messages are normally queried)

* Level 3: Write a unit test for `SyncAirbnb`. Note that you cannot call the airbnb or dynamodb clients in your test (since these are live APIs), so you will need to mock their responses, either manually or by copying/modifying the contents of `threads.json`. Inject those dependancies!
<!--stackedit_data:
eyJoaXN0b3J5IjpbLTE0NTAxNDIwMDgsMTUzOTk5MjU4Niw1OT
M2NzAzNF19
-->