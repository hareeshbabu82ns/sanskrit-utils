
import os
from pymongo import MongoClient, IndexModel, ASCENDING, TEXT

# MONGO_DB_PASSWORD = pwd  \
#     MONGO_DB_HOST = 192.168.0.10  \
#     MONGO_DB_PORT = 3333  \
#     python sanskrit_utils/loaders/SetupMongodb.py

mdbHost = os.environ.get('MONGO_DB_HOST', 'localhost')
mdbPort = os.environ.get('MONGO_DB_PORT', '21017')
mdbDB = os.environ.get('MONGO_DB_DB', 'sansutils')
mdbUser = os.environ.get('MONGO_DB_USER', 'sansutils')
mdbPassword = os.environ.get('MONGO_DB_PASSWORD', '')

# mongodb://sansutils:pwd@192.168.0.10:3333/sansutils
mdbUrl = f'mongodb://{mdbUser}:{mdbPassword}@{mdbHost}:{mdbPort}/{mdbDB}'
# mdbUrl = 'mongodb://{mdbUser}:{mdbPassword}'
print('MongoDB connecting to:', mdbUrl)

myclient = MongoClient(mdbUrl)

mydb = myclient[mdbDB]

dictEntriesCollection = mydb["dictEntries"]

indexes = []

wordKey = IndexModel([("wordOriginal", ASCENDING), ("word.slp1", ASCENDING)],
                     name="word-key", background=True)
indexes.append(wordKey)

# wordOriginal = IndexModel([("wordOriginal", ASCENDING)],
#                           name="word-original", background=True)
# indexes.append(wordOriginal)

# wordCompound = IndexModel([("word.$**", ASCENDING)],
#                           name="word-cmp", background=True)
# indexes.append(wordCompound)

wordSlp = IndexModel([("word.slp1", ASCENDING)],
                     name="word-slp", background=True)
indexes.append(wordSlp)

descKey = IndexModel([("descOriginal", ASCENDING), ("desc.slp1", ASCENDING)],
                     name="desc-key", background=True)
indexes.append(descKey)

# descOriginal = IndexModel([("descOriginal", ASCENDING)],
#                           name="desc-original", background=True)
# indexes.append(descOriginal)

# descCompound = IndexModel([("desc.$**", ASCENDING)],
#                           name="desc-cmp", background=True)
# indexes.append(descCompound)

descSlp = IndexModel([("desc.slp1", ASCENDING)],
                     name="desc-slp", background=True)
indexes.append(descSlp)

fts = IndexModel([
    ("wordOriginal", TEXT), ("word.slp1", TEXT),
    # ("word.devanagari", TEXT), ("word.telugu", TEXT), ("word.iast", TEXT),
    ("descOriginal", TEXT), ("desc.slp1", TEXT),
    # ("desc.devanagari", TEXT), ("desc.telugu", TEXT), ("desc.iast", TEXT),
], name="word-desc-fts", background=True)
indexes.append(fts)

dictBrowse = IndexModel([("origin", ASCENDING), ("word", ASCENDING)],
                     name="dict-browse", background=True)
indexes.append(dictBrowse)

dictEntriesCollection.drop_indexes()
dictEntriesCollection.create_indexes(indexes)
