import enum
from ariadne import ObjectType, exceptions
from sanskrit_utils.schema import query
from indic_transliteration import sanscript
from sanskrit_parser import Parser
from sanskrit_parser.base.sanskrit_base import SanskritObject, SanskritNormalizedString, SLP1, SCHEMES as PARSER_SCHEMES
from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer

from sanskrit_utils.schema.Sanscript import SanscriptScheme

analyzer = LexicalSandhiAnalyzer()
parser = Parser()

# reverse key values
SANS_TO_PARSER_SCHEMES_MAP = {v: k for k, v in PARSER_SCHEMES.items()}


@query.field("splits")
def res_q_splits(_, info, text, schemeFrom=SanscriptScheme.DEVANAGARI,
                 schemeTo=SanscriptScheme.SLP1, strictIO=False, limit=10):
    """ Get lexical tags for text """
    parser.strict_io = strictIO
    parser.input_encoding = schemeFrom.value
    parser.output_encoding = schemeTo.value

    splits = parser.split(text, limit=limit)
    jsplits = [[ss.transcoded(schemeTo.value, strictIO)
                for ss in s.split] for s in splits]
    # print(jsplits)
    return jsplits

    # strict_p = strictIO
    # vobj = SanskritObject(text, strict_io=strict_p,
    #                       replace_ending_visarga=None)
    # g = analyzer.getSandhiSplits(vobj)
    # if g:
    #     splits = g.find_all_paths(10)
    #     jsplits = [[ss.transcoded(schemeTo.value)
    #                 for ss in s] for s in splits]
    # else:
    #     jsplits = []
    # # r = {"input": text, "devanagari": vobj.devanagari(), "splits": jsplits}
    # # print(jsplits)
    # return jsplits


@query.field("joins")
def res_q_joins(_, info, words=[], schemeFrom=SanscriptScheme.DEVANAGARI, schemeTo=SanscriptScheme.SLP1, strictIO=False):

    joins = []

    if len(words) < 2:
        return exceptions.HttpBadRequestError('Too few words to join')

    words_normalized = [SanskritNormalizedString(
        word, encoding=schemeFrom.value, strict_io=strictIO) for word in words]
    print(words_normalized)

    first_in = words_normalized.pop(0)
    second_in = words_normalized.pop(0)

    joins = join_2_words(first_in, second_in, schemeTo, strictIO)
    print(joins)

    if len(words) > 2:
        for word in words_normalized:
            tmp_joins = [join_2_words(join, word) for join in joins]
            print(tmp_joins)
            joins = tmp_joins[0]

    sjoins = [join.transcoded(
        schemeTo.value, strictIO) for join in joins]

    # remove duplicates
    sjoins = list(dict.fromkeys(sjoins))
    # print(sjoins)
    return sjoins


def join_2_words(first_in, second_in, schemeTo=SanscriptScheme.SLP1, strictIO=False):
    joins = analyzer.sandhi.join(first_in, second_in)
    sjoins = [SanskritNormalizedString(
        join, encoding=SLP1, strict_io=strictIO) for join in list(joins)]
    return sjoins


def jedge(pred, node, label):
    return (node.pada.devanagari(strict_io=False),
            jtag(node.getMorphologicalTags()),
            SanskritObject(label, encoding=SLP1).devanagari(strict_io=False),
            pred.pada.devanagari(strict_io=False))


def jnode(node):
    """ Helper to translate parse node into serializable format"""
    return (node.pada.devanagari(strict_io=False),
            jtag(node.getMorphologicalTags()), "", "")


def jtag(tag):
    """ Helper to translate tag to serializable format"""
    return (tag[0].devanagari(strict_io=False), [t.devanagari(strict_io=False) for t in list(tag[1])])


def jtags(tags):
    """ Helper to translate tags to serializable format"""
    return [jtag(x) for x in tags]


# @api.route('/version/')
# class Version(Resource):
#     def get(self):
#         """Library Version"""
#         r = {"version": str(__version__)}
#         return r


# @api.route('/tags/<string:p>')
# class Tags(Resource):
#     def get(self, p):
#         """ Get lexical tags for p """
#         pobj = SanskritObject(p, strict_io=False)
#         tags = analyzer.getMorphologicalTags(pobj)
#         if tags is not None:
#             ptags = jtags(tags)
#         else:
#             ptags = []
#         r = {"input": p, "devanagari": pobj.devanagari(), "tags": ptags}
#         return r


# @api.route('/parse-presegmented/<string:v>')
# class Parse_Presegmented(Resource):
#     def get(self, v):
#         """ Parse a presegmented sentence """
#         strict_p = True
#         if request.args.get("strict") == "false":
#             strict_p = False
#         vobj = SanskritObject(v, strict_io=strict_p, replace_ending_visarga=None)
#         parser = Parser(input_encoding="SLP1",
#                         output_encoding="Devanagari",
#                         replace_ending_visarga='s')
#         mres = []
#         print(v)
#         for split in parser.split(vobj.canonical(), limit=10, pre_segmented=True):
#             parses = list(split.parse(limit=10))
#             sdot = split.to_dot()
#             mres = [x.serializable() for x in parses]
#             pdots = [x.to_dot() for x in parses]
#         r = {"input": v, "devanagari": vobj.devanagari(), "analysis": mres,
#              "split_dot": sdot,
#              "parse_dots": pdots}
#         return r


# @api.route('/presegmented/<string:v>')
# class Presegmented(Resource):
#     def get(self, v):
#         """ Presegmented Split """
#         vobj = SanskritObject(v, strict_io=True, replace_ending_visarga=None)
#         parser = Parser(input_encoding="SLP1",
#                         output_encoding="Devanagari",
#                         replace_ending_visarga='s')
#         splits = parser.split(vobj.canonical(), limit=10, pre_segmented=True)
#         r = {"input": v, "devanagari": vobj.devanagari(), "splits": [x.serializable()['split'] for x in splits]}
#         return r
