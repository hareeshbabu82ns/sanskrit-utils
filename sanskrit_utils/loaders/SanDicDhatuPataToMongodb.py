import os
import sqlite3
import pymongo
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

SANSCRIPT_LANGS = [sanscript.DEVANAGARI,
                   sanscript.IAST, sanscript.SLP1, sanscript.TELUGU]

# MONGO_DB_PASSWORD = pwd  \
#     MONGO_DB_HOST = 192.168.0.10  \
#     MONGO_DB_PORT = 3333  \
#     python sanskrit_utils/loaders/SanDicDhatuPataToMongodb.py

mdbHost = os.environ.get('MONGO_DB_HOST', 'localhost')
mdbPort = os.environ.get('MONGO_DB_PORT', '21017')
mdbDB = os.environ.get('MONGO_DB_DB', 'sansutils')
mdbUser = os.environ.get('MONGO_DB_USER', 'sansutils')
mdbPassword = os.environ.get('MONGO_DB_PASSWORD', '')

# mongodb://sansutils:pwd@192.168.0.10:3333/sansutils
mdbUrl = f'mongodb://{mdbUser}:{mdbPassword}@{mdbHost}:{mdbPort}/{mdbDB}'
print('MongoDB connecting to:', mdbUrl)

myclient = pymongo.MongoClient(mdbUrl)

mydb = myclient[mdbDB]

dictEntriesCollection = mydb["dictEntries"]


def convert_text(text, fr=sanscript.DEVANAGARI, to=sanscript.ITRANS):
    return transliterate(text, fr, to)


def get_word_transripts(text):
    data = {}
    for lang in SANSCRIPT_LANGS:
        data[lang] = convert_text(text, to=lang)
    return data


def push_to_mongodb():
    con = sqlite3.connect('tmp/sandic.db')
    cur = con.cursor()

    # cur.execute("SELECT * FROM dictEntries_content")
    # cur.fetchone()

    for row in cur.execute('SELECT * FROM dictEntries_content ORDER BY docid'):
        record = {"wordOriginal": row[1],
                  "wordIndex": row[2],
                  "descOriginal": row[3],
                  "origin": row[4]}
        record['word'] = get_word_transripts(row[1])
        record['desc'] = get_word_transripts(row[3])
        dictEntriesCollection.insert_one(record)
        print(row[1])

    con.close()


if __name__ == '__main__':
    push_to_mongodb()
    # add_itrans_convertions()
