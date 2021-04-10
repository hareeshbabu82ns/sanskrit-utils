import enum
import pymongo
from ariadne import EnumType, ObjectType
from sanskrit_utils.schema import query
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

from sanskrit_utils.database import dictEntriesCollection
# from sanskrit_utils.database import mongodbClient, mdbDB

dictionaryItem = ObjectType('DictionaryItem')

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

# @dictionaryItem.field("key")
# def res_q_dict_item_key(record, info, scheme=SanscriptScheme.DEVANAGARI):
#     print(record)
#     key = record['word'][scheme.value] if record['word'].get(
#         scheme.value) else record['wordOriginal']
#     return key


@query.field("dictionarySearch")
def res_q_dict_search(_, info, searchWith):
    search = searchWith['search']
    searchScheme = searchWith.get('searchScheme', SanscriptScheme.SLP1)
    fuzzySearch = searchWith.get('fuzzySearch', False)
    searchOnlyKeys = searchWith.get('searchOnlyKeys', False)
    caseInsensitive = searchWith.get('caseInsensitive', False)
    startsWith = searchWith.get('startsWith', False)
    endsWith = searchWith.get('endsWith', False)
    origin = searchWith.get('origin', [])
    outputScheme = searchWith.get('outputScheme', SanscriptScheme.DEVANAGARI)
    limit = searchWith.get('limit', 100)

    requestedOutputFields = [
        node.name.value for node in info.field_nodes[0].selection_set.selections]

    searchFilter = {}

    finalSearch = search if searchScheme == SanscriptScheme.SLP1 else transliterate(
        search, searchScheme.value, sanscript.SLP1)

    if fuzzySearch:
        searchFilter = {'$text': {'$search': finalSearch}}
    else:
        if startsWith:
            finalSearch = '^' + finalSearch
        if endsWith:
            finalSearch = finalSearch + '$'
        regexOptions = ''
        if caseInsensitive:
            regexOptions = 'i'

        print(finalSearch)
        searchRegex = {'$regex': finalSearch, '$options': regexOptions}
        searchFilter = []
        searchFilter.append({'wordOriginal': searchRegex})
        searchFilter.append({f'word.{sanscript.SLP1}': searchRegex})
        if not searchOnlyKeys:
            searchFilter.append({'descOriginal': searchRegex})
            searchFilter.append({f'desc.{sanscript.SLP1}': searchRegex})
        searchFilter = {'$or': searchFilter}

    print(searchFilter)

    if len(origin) > 0:
        searchFilter['origin'] = {}
        searchFilter['origin']['$in'] = [o.value for o in origin]

    # projectionFilter = {"_id": 1,
    #                     "wordOriginal": 1 if 'key' in requestedOutputFields else 0,
    #                     "word": 1 if 'key' in requestedOutputFields else 0,
    #                     "descOriginal": 1 if 'description' in requestedOutputFields else 0,
    #                     "desc": 1 if 'description' in requestedOutputFields else 0
    #                     }
    projectionFilter = {"_id": 1, "origin": 1}
    if 'key' in requestedOutputFields:
        projectionFilter["wordOriginal"] = 1
        projectionFilter["word"] = 1

    if 'description' in requestedOutputFields:
        projectionFilter["descOriginal"] = 1
        projectionFilter["desc"] = 1

    data = dictEntriesCollection.find(
        searchFilter, projectionFilter).limit(limit)
    results = []
    # print([(color.value, color.name) for color in Dictionaries])
    for record in data:
        # print(record)
        item = {'id': record['_id'],
                'origin': Dictionaries(record['origin'])}

        if 'key' in requestedOutputFields:
            item['key'] = record['word'][outputScheme.value] if record['word'].get(
                outputScheme.value) else record['wordOriginal']
        if 'description' in requestedOutputFields:
            item['description'] = record['desc'][outputScheme.value] if record['desc'].get(
                outputScheme.value) else record['descOriginal']

        results.append(item)
        # print(item)
        # break
    return results
