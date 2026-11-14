import os
import pymongo

mdbHost = os.environ.get('MONGO_DB_HOST', 'localhost')
mdbPort = os.environ.get('MONGO_DB_PORT', '27017')
mdbDB = os.environ.get('MONGO_DB_DB', 'sansutils')
mdbUser = os.environ.get('MONGO_DB_USER', 'sansutils')
mdbPassword = os.environ.get('MONGO_DB_PASSWORD', '')

# Without a password, connect unauthenticated (e.g. a local MongoDB without auth).
mdbAuth = f'{mdbUser}:{mdbPassword}@' if mdbPassword else ''
mdbUrl = f'mongodb://{mdbAuth}{mdbHost}:{mdbPort}/{mdbDB}'
print(f"MongoDB connecting to: mongodb://{mdbUser + ':***@' if mdbPassword else ''}{mdbHost}:{mdbPort}/{mdbDB}")

# connect=False: the connection is opened lazily on first query, so the API
# starts (and non-DB queries like transliterate/splits work) without MongoDB.
mongodbClient = pymongo.MongoClient(mdbUrl, connect=False)

dbConnection = mongodbClient[mdbDB]

dictEntriesCollection = dbConnection["dictEntries"]

dictPhoneticsEntriesCollection = dbConnection["dictPhonetics"]
