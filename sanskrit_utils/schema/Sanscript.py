import enum
import pymongo
from ariadne import EnumType
from sanskrit_utils.schema import query
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

from sanskrit_utils.database import dictEntriesCollection
# from sanskrit_utils.database import mongodbClient, mdbDB

# sanscriptSchemesEnum = EnumType("SanscriptScheme",{
#   "DEVANAGARI" : sanscript.DEVANAGARI,
#   "IAST" : sanscript.IAST,
#   "ITRANS" : sanscript.ITRANS,
#   "SLP1" : sanscript.SLP1,
#   "TELUGU" : sanscript.TELUGU,
#   "TAMIL" : sanscript.TAMIL,
#   "KANNADA" : sanscript.KANNADA
# })


class SanscriptScheme(enum.Enum):
    DEVANAGARI = sanscript.DEVANAGARI
    IAST = sanscript.IAST
    ITRANS = sanscript.ITRANS
    SLP1 = sanscript.SLP1
    TELUGU = sanscript.TELUGU
    TAMIL = sanscript.TAMIL
    KANNADA = sanscript.KANNADA


sanscriptSchemesEnum = EnumType("SanscriptScheme", SanscriptScheme)


class Dictionaries(enum.Enum):
    VCP = 'vcp'
    DHATU_PATA = 'Dhātu-pāṭha'
    MW = 'mw'
    MWE = 'mwe'
    SKD = 'skd'


dictionaryEnum = EnumType("Dictionary", Dictionaries)


@query.field("transliterate")
def res_q_transliterate(_, info, text, schemeFrom=SanscriptScheme.DEVANAGARI, schemeTo=SanscriptScheme.SLP1):
    # return f'{text},{schemeFrom},{schemeTo}'
    return transliterate(text, schemeFrom.value, schemeTo.value)


@query.field("dictionaryFuzzySearch")
def res_q_dict_fuzzy_search(_, info, search, origin=[],
                            scheme=SanscriptScheme.DEVANAGARI, limit=100):

    searchFilter = {'$text': {'$search': search}}
    if len(origin) > 0:
        searchFilter['origin'] = {}
        searchFilter['origin']['$in'] = [o.value for o in origin]

    projectionFilter = {"_id": 0
                        # "word": 0, "desc": 0
                        }

    data = dictEntriesCollection.find(
        searchFilter, projectionFilter).limit(limit)
    results = []
    # print([(color.value, color.name) for color in Dictionaries])
    for record in data:
        # print(record)
        key = record['word'][scheme.value] if record['word'].get(
            scheme.value) else record['wordOriginal']
        description = record['desc'][scheme.value] if record['desc'].get(
            scheme.value) else record['descOriginal']
        item = {'key': key,
                'description': description,
                'origin': Dictionaries(record['origin'])}
        results.append(item)
        # print(item)
    return results


@query.field("dictionaryKeySearch")
def res_q_dict_key_search(_, info, search, caseInsensitive=False,
                          startsWith=False, endsWith=False,
                          origin=[], scheme=SanscriptScheme.DEVANAGARI,
                          limit=100):

    finalSearch = search
    if startsWith:
        finalSearch = '^' + finalSearch
    # finalSearch = finalSearch + search
    if endsWith:
        finalSearch = finalSearch + '$'
    # finalSearch = finalSearch + '\\'
    regexOptions = ''
    if caseInsensitive:
        regexOptions = 'i'

    print(finalSearch)
    searchFilter = {'wordOriginal': {
        '$regex': finalSearch, '$options': regexOptions}}
    if len(origin) > 0:
        searchFilter['origin'] = {}
        searchFilter['origin']['$in'] = [o.value for o in origin]

    projectionFilter = {"_id": 0
                        # "word": 0, "desc": 0
                        }

    data = dictEntriesCollection.find(
        searchFilter, projectionFilter).limit(limit)
    results = []
    # print([(color.value, color.name) for color in Dictionaries])
    for record in data:
        # print(record)
        key = record['word'][scheme.value] if record['word'].get(
            scheme.value) else record['wordOriginal']
        description = record['desc'][scheme.value] if record['desc'].get(
            scheme.value) else record['descOriginal']
        item = {'key': key,
                'description': description,
                'origin': Dictionaries(record['origin'])}
        results.append(item)
        # print(item)
    return results
