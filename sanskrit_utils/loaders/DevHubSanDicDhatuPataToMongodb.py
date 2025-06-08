import datetime
import os
import sqlite3
import pymongo
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

SANSCRIPT_LANGS = [sanscript.DEVANAGARI, sanscript.ITRANS,
                   sanscript.IAST, sanscript.SLP1, sanscript.TELUGU]

SANSCRIPT_LANGS_TO_DB = {
    sanscript.DEVANAGARI: 'SAN',
    sanscript.IAST: 'IAST',
    sanscript.ITRANS: 'ITRANS',
    sanscript.SLP1: 'SLP1',
    sanscript.TELUGU: 'TEL'
}

# MONGO_DB_PASSWORD = pwd  \
#     MONGO_DB_HOST = 192.168.0.10  \
#     MONGO_DB_PORT = 3333  \
#     python sanskrit_utils/loaders/DevHubSanDicDhatuPataToMongodb.py

mdbHost = os.environ.get('MONGO_DB_HOST', 'localhost')
mdbPort = os.environ.get('MONGO_DB_PORT', '21017')
mdbDB = os.environ.get('MONGO_DB_DB', 'devhubjs')
mdbUser = os.environ.get('MONGO_DB_USER', 'devhubjs')
mdbPassword = os.environ.get('MONGO_DB_PASSWORD', '')

# mongodb://devhubjs:pwd@192.168.0.10:3333/devhubjs
mdbUrl = f'mongodb://{mdbUser}:{mdbPassword}@{mdbHost}:{mdbPort}/{mdbDB}'
print('MongoDB connecting to:', mdbUrl)

myclient = pymongo.MongoClient(mdbUrl)

mydb = myclient[mdbDB]

dictEntriesCollection = mydb["DictWords"]


def convert_text(text, fr=sanscript.DEVANAGARI, to=sanscript.ITRANS):
    return transliterate(text, fr, to)


def get_word_transripts(text):
    data = []
    for lang in SANSCRIPT_LANGS:
        data.append(
            {"lang": SANSCRIPT_LANGS_TO_DB[lang], "value": convert_text(text, to=lang)})
    return data


def push_to_mongodb():
    con = sqlite3.connect('tmp/dhatu_pata.sqlite')
    cur = con.cursor()

    # cur.execute("SELECT * FROM dictEntries_content")
    # cur.fetchone()
    index = 0
    for row in cur.execute('SELECT * FROM dictEntries_content ORDER BY docid'):
        record = {
            "wordIndex": index,
            "wordLnum": row[2],
            "phonetic": "",
            "origin": 'DHATU_PATA',
        }
        record['word'] = get_word_transripts(row[1])
        record['description'] = get_word_transripts(row[3])
        record['createdAt'] = record['updatedAt'] = datetime.datetime.now()

        attributes = []
        attributes.append(
            {"key": "wordOriginal", "value": row[1]})
        attributes.append(
            {"key": "wordOriginalLang", "value": "SAN"})
        attributes.append(
            {"key": "descOriginal", "value": row[3]})
        attributes.append(
            {"key": "descOriginalLang", "value": "SAN"})

        record['attributes'] = attributes

        dictEntriesCollection.insert_one(record)
        index += 1
        # print(record)

    con.close()


if __name__ == '__main__':
    push_to_mongodb()
    # add_itrans_convertions()
