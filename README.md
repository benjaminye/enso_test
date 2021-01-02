# Set Up

## Via Poetry
Make sure to have [Poetry](https://python-poetry.org/) installed
### Installing Dependencies
```
# Clone Repo
$ git clone https://github.com/benjaminye/enso_test.git

# Install dependencies
$ cd enso_test
$ poetry install
```
### Running Modules/Tests
```
# Running commands with virtual environment 
$ poetry run pytest
$ poetry run python sync.py
```
or
```
# Switching to shell with virtual envinronment activated
$ poetry shell

# Running commands with virtual environment
$ pytest
$ python sync.py
```

## Via venv
### Installing Dependencies
```
# Clone Repo
$ git clone https://github.com/benjaminye/enso_test.git
$ cd enso_test

# Create virtual environment
$ python -m venv venv

# Activate virtual environment
$ ./venv/Scripts/activate.ps1 # Windows Powershell
$ source ./venv/bin/activate # Unix

# Install dependencies
$ pip install -r requirements.txt
```
### Running Modules/Tests
```
# With virtualenv activated
$ pytest
$ python sync.py
```



# AWS Credentials / Regions
## Credentials File
By default, `db.py` looks for `./credentials` file for AWS credentials with following format:
```
[default]
aws_access_key_id=foo
aws_secret_access_key=bar
```
You can change this default behaviour by editing `db.py` file line 11:
```
os.environ["AWS_SHARED_CREDENTIALS_FILE"]  =  <<desired_path>>
```
## Default Region
By default, `db.py` looks for AWS resources in US East 1.

You can change this default behaviour by editing `db.py` file line 12:
```
os.environ["AWS_DEFAULT_REGION"]  =  <<desired_region>>
```

# Creating/Connecting DynamoDB resource
When creating an instance of `DBDynamo` class, you have to pass in `table_name` parameter.
It will first look for a DynamoDB (using configured credentials & region) table with that name. If not found, the instance will try to create a new table using the `table_name` passed in with correct configurations.

By default, the table will be created with 5 RCUs and 5WCUs; to change the behaviour, edit `db.py` file line 329:
```
328			...
329			ProvisionedThroughput={"ReadCapacityUnits":  <<RCU #>>,  "WriteCapacityUnits":  <<WCU #>>},
330			...
```



# DynamoDB schema
|itemType (partition_key)|itemID(sort_key)  | itemData |
|--|--|--|
| guest | host_id#updated_at#guest_id | {guest_id: "111", sent: 1000, ...} |
| msg | host_id#sent#*hash* |{guest_id: "111", updated_at: 1000, ...} |

**Note:** *hash* is used to prevent key collision when there are multiple messages sent at the same timestamp. Current implementation of the hash is such that the **first** and **second** message with the same timestamp will have hash of **0** and **1**, respectively.  




# Performance Improvement Ideas
## Batch Writing
Currently, at each update step, guests are compared & updated to the database each time a thread is scanned, and messages are compared & updated each time a message is scanned from the thread.  

We can implement a stack for each update step. And add updates we needed to make on guests and messages to the stack. Only at the end of the update step will we commit those updates to the database in batch. This leverages boto3's `batch_writer()` method for DynamoDB table to increase speed and reduce number of requests.


## Database Read Caching
During each comparison step for messages, `SyncAirbnb` will attempt to read the database. Often times, it will try to read the same set of records. We can reduce the number of requests sent to the database by implementing a caching scheme either in-code (for example `functools.cache()`) or have a caching server.

## Partial Message Comparison
When comparing messages received from the client, `SyncAirbnb` compares every message in the response with the database. Logically, we can stop the comparison right when we've found an old messages (since all the following messages will be old as well).
But of course, this assumes that the messaging client we receive data from won't miss any previous messages -- which might happen sometimes when its databases failed to sync up.
