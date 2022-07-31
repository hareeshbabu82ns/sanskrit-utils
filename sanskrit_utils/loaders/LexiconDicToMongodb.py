import os
import sqlite3
import pymongo
from lexicon_parser import LexiconHTMLParser
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

# MONGO_DB_PASSWORD = pwd  \
#     MONGO_DB_HOST = 192.168.0.10  \
#     MONGO_DB_PORT = 3333  \
#     python sanskrit_utils/loaders/LexiconDicToMongodb.py

mdbHost = os.environ.get('MONGO_DB_HOST', 'localhost')
mdbPort = os.environ.get('MONGO_DB_PORT', '21017')
mdbDB = os.environ.get('MONGO_DB_DB', 'sansutils')
mdbUser = os.environ.get('MONGO_DB_USER', 'sansutils')
mdbPassword = os.environ.get('MONGO_DB_PASSWORD', '')

# mongodb://sansutils:pwd@192.168.0.10:3333/sansutils
mdbUrl = f'mongodb://{mdbUser}:{mdbPassword}@{mdbHost}:{mdbPort}/{mdbDB}'
# mdbUrl = 'mongodb://{mdbUser}:{mdbPassword}'
print('MongoDB connecting to:', mdbUrl)

myclient = pymongo.MongoClient(mdbUrl)

mydb = myclient[mdbDB]

dictEntriesCollection = mydb["dictEntries"]
SANS_WORD_TAG = {
    'bhs': 'b',
    'ieg': 'i',
    'inm': 'i',
    'lan': 'b',
    'mci': 'b',
    'pgn': 'i',
    'pui': 'i',
    'snp': 'i',
    'vei': 'b',
    'default': 's',
}
# Dictionaries
LEXICON_DICT_LIST = [
    'acc',    'ae',    'ap90',    'armh',    'ben',
    'bhs',    'bor',    'cae',    'gst',    'ieg',
    'inm',    'krm',    'lan',    'mci',    'md',
    'mw',    'mw72',    'mwe',    'pe',    'pgn',
    'pui',    'shs',    'skd',    'snp',    'vcp',
    'vei',    'wil',    'yat'
]
# LEXICON_DICT_LIST = ['bhs', 'ieg', 'vcp', 'mwe']
# LEXICON_DICT_LIST = ["vcp", "skd", "mw", "mwe"]
LEXICON_SAN_DICT_LIST = [
    'acc', 'ap90', 'armh', 'ben',
    'bhs', 'cae', 'gst', 'ieg',
    'inm', 'krm', 'lan', 'mci',
    'md', 'mw', 'mw72', 'pe',
    'pui', 'shs', 'skd', 'snp',
    'vcp', 'vei', 'wil', 'yat'
]

SANSCRIPT_LANGS = [sanscript.DEVANAGARI,
                   sanscript.IAST, sanscript.SLP1, sanscript.TELUGU]


def convert_text(text, fr=sanscript.SLP1, to=sanscript.ITRANS):
    return transliterate(text, fr, to)


def push_to_mongodb(con, dictName):
    cur = con.cursor()
    print('working on dictionary: ', dictName)
    for row in cur.execute(f'SELECT * FROM {dictName}'):
        record = {"wordOriginal": row[0],
                  "wordIndex": row[1],
                  "descOriginal": row[2],
                  "origin": dictName}

        record['word'] = get_word_transripts(row[0], dictName)
        record['desc'] = get_desc_transripts(row[2], dictName)

        # print('\ndesc original: \n', record['descOriginal'])
        # print('\ndesc tel: \n', record['desc']['telugu'])
        dictEntriesCollection.insert_one(record)
        # print(dictName, row[0])
        # print(dictName, '\n', record)
        # limit number of records to upload (for testing)
        # if(row[1] > 2):
        #     break

    con.close()


def get_desc_transripts(text, dictName):
    data = {}
    for lang in SANSCRIPT_LANGS:
        data[lang] = convert_lexicon_html_to_markdown(
            dictName, text, toLang=lang)
    return data


def get_word_transripts(text, dictName):
    data = {}
    if dictName in LEXICON_SAN_DICT_LIST:
        for lang in SANSCRIPT_LANGS:
            data[lang] = convert_text(text, to=lang)
    else:
        data['english'] = text
    return data


def convert_lexicon_html_to_markdown(dictionary,  content, toLang=sanscript.DEVANAGARI):
    sans_word_tag = SANS_WORD_TAG.get(dictionary, 's')
    sans_word_lang = sanscript.IAST if sans_word_tag in [
        'i', 'b'] else sanscript.SLP1
    parser = LexiconHTMLParser()
    if dictionary in LEXICON_SAN_DICT_LIST:
        parser.init(
            sans_word_tag=sans_word_tag,
            key_fromLang=sanscript.SLP1,
            key_toLang=toLang,
            fromLang=sans_word_lang,
            toLang=toLang)
    else:
        parser.init(
            key_fromLang=sanscript.SLP1,
            key_toLang=sanscript.SLP1,
            toLang=toLang)
    parser.feed(content)

    return parser.mark_down


def add_lexicon_dict_convertions():
    for dictName in LEXICON_DICT_LIST:
        con = sqlite3.connect(f'tmp/{dictName}.sqlite')
        push_to_mongodb(con, dictName)


if __name__ == '__main__':
    add_lexicon_dict_convertions()
