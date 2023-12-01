import enum
import pymongo
from bson.objectid import ObjectId
from ariadne import EnumType, ObjectType
from graphql import GraphQLError
from sanskrit_utils.schema import query, mutation
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

from sanskrit_utils.database import dictEntriesCollection, dictPhoneticsEntriesCollection
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
    ENGLISH = 'english'


sanscriptSchemesEnum = EnumType("SanscriptScheme", SanscriptScheme)


class Dictionaries(enum.Enum):
    DHATU_PATA = 'dhatus'
    ENG2TEL = 'eng2te'  # various English to Telugu Dictionaries
    # Sanskrit-English Dictionaries
    WIL = 'wil'  # 1832	Wilson Sanskrit-English Dictionary
    YAT = 'yat'  # 1846	Yates Sanskrit-English Dictionary
    GST = 'gst'  # 1856	Goldstücker Sanskrit-English Dictionary
    BEN = 'ben'  # 1866	Benfey Sanskrit-English Dictionary
    MW72 = 'mw72'  # 1872	Monier-Williams Sanskrit-English Dictionary
    LAN = 'lan'  # 1884	Lanman`s Sanskrit Reader Vocabulary
    AP90 = 'ap90'  # 1890	Apte Practical Sanskrit-English Dictionary
    CAE = 'cae'  # 1891	Cappeller Sanskrit-English Dictionary
    MD = 'md'  # 1893	Macdonell Sanskrit-English Dictionary
    MW = 'mw'  # 1899	Monier-Williams Sanskrit-English Dictionary
    SHS = 'shs'  # 1900	Shabda-Sagara Sanskrit-English Dictionary
    AP = 'ap'  # 1957	Practical Sanskrit-English Dictionary
    PD = 'pd'  # 1976	An Encyclopedic Dictionary

    # English-Sanskrit Dictionaries
    MWE = 'mwe'  # 1851	Monier-Williams English-Sanskrit Dictionary
    BOR = 'bor'  # 1877	Borooah English-Sanskrit Dictionary
    AE = 'ae'  # 1920	Apte Student`s English-Sanskrit Dictionary

    # Sanskrit-Sanskrit Dictionaries
    ARMH = 'armh'  # 1861	Abhidhānaratnamālā of Halāyudha
    VCP = 'vcp'  # 1873	Vacaspatyam
    SKD = 'skd'  # 1886	Sabda-kalpadruma

    # Specialized Dictionaries
    INM = 'inm'  # 1904	Index to the Names in the Mahabharata
    VEI = 'vei'  # 1912	The Vedic Index of Names and Subjects
    PUI = 'pui'  # 1951	The Purana Index
    BHS = 'bhs'  # 1953	Edgerton Buddhist Hybrid Sanskrit Dictionary
    ACC = 'acc'  # 1962	Aufrecht's Catalogus Catalogorum
    KRM = 'krm'  # 1965	Kṛdantarūpamālā
    IEG = 'ieg'  # 1966	Indian Epigraphical Glossary
    SNP = 'snp'  # 1974	Meulenbeld's Sanskrit Names of Plants
    PE = 'pe'  # 1975	Puranic Encyclopedia
    PGN = 'pgn'  # 1978	Personal and Geographical Names in the Gupta Inscriptions
    MCI = 'mci'  # 1993	Mahabharata Cultural Index

    OTHERS = 'others'  # any other generic entries


dictionaryEnum = EnumType("Dictionary", Dictionaries)


def prepare_dict_item_from_input(withData, update=False):
    word_original = withData.get('word')
    desc_original = withData.get('description')

    word_translations = withData.get('wordTranslations')
    desc_translations = withData.get('descriptionTranslations')

    word_dict = {}
    if word_translations is not None and isinstance(word_translations, list):
        for item in word_translations:
            word_dict[SanscriptScheme(item['language']).value] = item['value']
        if word_original is None and len(word_translations) > 0:
            word_original = word_translations.pop(0).get('value')
    if word_original is None:
        word_original = ''

    desc_dict = {}
    if desc_translations is not None and isinstance(desc_translations, list):
        for item in desc_translations:
            desc_dict[SanscriptScheme(item['language']).value] = item['value']
        if desc_original is None and len(desc_translations) > 0:
            desc_original = desc_translations.pop(0).get('value')
    if desc_original is None:
        desc_original = ''

    origin = withData.get('origin')
    origin = Dictionaries(
        origin).value if origin is not None else Dictionaries.OTHERS.value

    transformed_data = {}
    if (update):
        if withData.get('wordIndex') is not None:
            transformed_data['wordIndex'] = withData['wordIndex']
        if withData.get('origin') is not None:
            transformed_data['origin'] = Dictionaries(origin).value
        if withData.get('word') is not None:
            transformed_data['wordOriginal'] = word_original,
        if withData.get('description') is not None:
            transformed_data['descOriginal'] = desc_original,
        if len(word_dict.items()) is not 0:
            transformed_data.update({'word': word_dict})
        if len(desc_dict.items()) is not 0:
            transformed_data.update({'desc': desc_dict}),
    else:
        transformed_data = {
            'wordIndex': withData['wordIndex'] if withData.get('wordIndex') is not None else 0,
            'wordOriginal': word_original,
            'descOriginal': desc_original,
            'word': word_dict,
            'desc': desc_dict,
            'origin': origin
        }

    return transformed_data


@mutation.field('createDictionaryItem')
def res_m_create_dict_item(_, info, withData):

    transformed_data_arr = []

    for data in withData:
        transformed_data = prepare_dict_item_from_input(data)
        transformed_data_arr.append(transformed_data)

    result = dictEntriesCollection.insert_many(transformed_data_arr)
    return result.inserted_ids


@mutation.field('updateDictionaryItem')
def res_m_update_dict_item(_, info, id, withData):
    transformed_data = prepare_dict_item_from_input(withData, update=True)

    update_operation = {'$set': transformed_data}
    result = dictEntriesCollection.update_one(
        {'_id': ObjectId(id)}, update_operation)

    if result.modified_count != 1:
        raise GraphQLError("No Dictionary Item found")

    return id


@mutation.field('deleteDictionaryItem')
def res_m_delete_dict_item(_, info, id):
    res = dictEntriesCollection.delete_one({'_id': ObjectId(id)})
    if res.deleted_count == 0:
        raise GraphQLError("No Dictionary Item found")

    return res.deleted_count


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


@query.field("dictionarySearchById")
def res_q_dict_item_by_id(_, info, id, outputScheme=SanscriptScheme.DEVANAGARI):

    record = dictEntriesCollection.find_one(ObjectId(id))
    item = {'id': record['_id'],
            'origin': Dictionaries(record['origin'])}

    item['key'] = record['word'][outputScheme.value] if record['word'].get(
        outputScheme.value) else record['wordOriginal']

    item['description'] = record['desc'][outputScheme.value] if record['desc'].get(
        outputScheme.value) else record['descOriginal']

    return item


@query.field("phoneticWordSearch")
def res_q_phonetic_search(_, info, searchWith):
    search = searchWith['search']
    searchScheme = searchWith.get('searchScheme', SanscriptScheme.SLP1)
    caseInsensitive = searchWith.get('caseInsensitive', False)
    startsWith = searchWith.get('startsWith', True)
    endsWith = searchWith.get('endsWith', False)
    outputScheme = searchWith.get('outputScheme', SanscriptScheme.SLP1)
    limit = searchWith.get('limit', 20)
    offset = searchWith.get('offset', 0)

    requestedOutputFields = [
        node.name.value for node in info.field_nodes[0].selection_set.selections]

    resultsIndex = -1
    try:
        resultsIndex = requestedOutputFields.index('results')
    except:
        resultsIndex = -1

    requestedResultOutputFields = [
        node.name.value for node in info.field_nodes[0].
        selection_set.selections[resultsIndex].selection_set.selections] if resultsIndex >= 0 else []

    searchFilter = {}

    finalSearch = search if searchScheme == SanscriptScheme.SLP1 else transliterate(
        search, searchScheme.value, sanscript.SLP1)

    if startsWith:
        finalSearch = '^' + finalSearch
    if endsWith:
        finalSearch = finalSearch + '$'
    regexOptions = ''
    if caseInsensitive:
        regexOptions = 'i'

    # print(finalSearch)
    searchRegex = {'$regex': finalSearch, '$options': regexOptions}
    searchFilter = {'_id': searchRegex}

    dataCount = dictPhoneticsEntriesCollection.count_documents(
        searchFilter) if 'total' in requestedOutputFields else 0

    data = dictPhoneticsEntriesCollection.find(
        searchFilter).limit(limit).skip(offset*limit).sort('word')

    results = []
    # print([(color.value, color.name) for color in Dictionaries])
    for record in data:
        # print(record)
        item = {'id': record['_id']}

        if 'key' in requestedResultOutputFields:
            item['key'] = record['_id']
        if 'word' in requestedResultOutputFields:
            item['word'] = record['word'] if outputScheme == SanscriptScheme.SLP1 else transliterate(
                record['word'], SanscriptScheme.SLP1.value, outputScheme.value)

        results.append(item)
        # print(item)
        # break

    searchData = {"total": dataCount, "results": results}
    return searchData


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
    offset = searchWith.get('offset', 0)

    requestedOutputFields = [
        node.name.value for node in info.field_nodes[0].selection_set.selections]

    resultsIndex = -1
    try:
        resultsIndex = requestedOutputFields.index('results')
    except:
        resultsIndex = -1

    requestedResultOutputFields = [
        node.name.value for node in info.field_nodes[0].
        selection_set.selections[resultsIndex].selection_set.selections] if resultsIndex >= 0 else []

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

        # print(finalSearch)
        searchRegex = {'$regex': finalSearch, '$options': regexOptions}
        searchFilter = []
        searchFilter.append({'wordOriginal': searchRegex})
        searchFilter.append({f'word.{sanscript.SLP1}': searchRegex})
        if not searchOnlyKeys:
            searchFilter.append({'descOriginal': searchRegex})
            searchFilter.append({f'desc.{sanscript.SLP1}': searchRegex})
        searchFilter = {'$or': searchFilter}

    # print(searchFilter)

    if len(origin) > 0:
        searchFilter['origin'] = {}
        searchFilter['origin']['$in'] = [o.value for o in origin]

    # projectionFilter = {"_id": 1,
    #                     "wordOriginal": 1 if 'key' in requestedResultOutputFields else 0,
    #                     "word": 1 if 'key' in requestedResultOutputFields else 0,
    #                     "descOriginal": 1 if 'description' in requestedResultOutputFields else 0,
    #                     "desc": 1 if 'description' in requestedResultOutputFields else 0
    #                     }
    projectionFilter = {"origin": 1}
    if 'key' in requestedResultOutputFields:
        projectionFilter["wordOriginal"] = 1
        projectionFilter["word"] = 1

    if 'description' in requestedResultOutputFields:
        projectionFilter["descOriginal"] = 1
        projectionFilter["desc"] = 1

    dataCount = dictEntriesCollection.count_documents(
        searchFilter) if 'total' in requestedOutputFields else 0

    data = dictEntriesCollection.find(
        searchFilter, projectionFilter
    ).limit(limit).skip(offset*limit).sort('word')

    results = []
    # print([(color.value, color.name) for color in Dictionaries])
    for record in data:
        # print(record)
        item = {'id': record['_id'],
                'origin': Dictionaries(record['origin'])}

        if 'key' in requestedResultOutputFields:
            item['key'] = record['word'][outputScheme.value] if record['word'].get(
                outputScheme.value) else record['wordOriginal']
        if 'description' in requestedResultOutputFields:
            item['description'] = record['desc'][outputScheme.value] if record['desc'].get(
                outputScheme.value) else record['descOriginal']

        results.append(item)
        # print(item)
        # break

    browseData = {"total": dataCount, "results": results}
    return browseData


@query.field("dictionaryBrowse")
def res_q_dict_browse(_, info, browseWith):
    origin = browseWith.get('origin', Dictionaries.VCP)
    outputScheme = browseWith.get('outputScheme', SanscriptScheme.DEVANAGARI)
    limit = browseWith.get('limit', 100)
    offset = browseWith.get('offset', 0)

    requestedOutputFields = [
        node.name.value for node in info.field_nodes[0].selection_set.selections]

    resultsIndex = -1
    try:
        resultsIndex = requestedOutputFields.index('results')
    except:
        resultsIndex = -1

    requestedResultOutputFields = [
        node.name.value for node in info.field_nodes[0].
        selection_set.selections[resultsIndex].selection_set.selections] if resultsIndex >= 0 else []

    searchFilter = {}
    searchFilter['origin'] = origin.value

    projectionFilter = {'_id': 1, 'origin': 1}
    if 'key' in requestedResultOutputFields:
        projectionFilter["wordOriginal"] = 1
        projectionFilter["word"] = 1

    if 'description' in requestedResultOutputFields:
        projectionFilter["descOriginal"] = 1
        projectionFilter["desc"] = 1

    dataCount = dictEntriesCollection.count_documents(
        searchFilter) if 'total' in requestedOutputFields else 0

    data = dictEntriesCollection.find(
        searchFilter, projectionFilter
    ).limit(limit).skip(offset*limit).sort('word') if 'results' in requestedOutputFields else []

    # data = dictEntriesCollection.find().limit(limit) if 'results' in requestedOutputFields else []

    results = []
    # print([(color.value, color.name) for color in Dictionaries])
    for record in data:
        # print(record)
        item = {'id': record['_id'],
                'origin': Dictionaries(record['origin'])}

        if 'key' in requestedResultOutputFields:
            item['key'] = record['word'][outputScheme.value] if record['word'].get(
                outputScheme.value) else record['wordOriginal']
        if 'description' in requestedResultOutputFields:
            item['description'] = record['desc'][outputScheme.value] if record['desc'].get(
                outputScheme.value) else record['descOriginal']

        results.append(item)
        # print(item)
        # break

    browseData = {"total": dataCount, "results": results}
    return browseData
