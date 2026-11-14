"""GraphQL resolvers for sandhi, morphology and vakya analysis.

The work is done in ``sanskrit_utils.parser_service``; these functions turn
GraphQL arguments into its arguments and its SLP1 results into `schemeTo`.
"""
from functools import wraps

from ariadne import ObjectType
from graphql import GraphQLError

from sanskrit_utils import parser_service as service
from sanskrit_utils.schema import query
from sanskrit_utils.schema.Sanscript import SanscriptScheme

parseType = ObjectType("Parse")
parseItemType = ObjectType("ParseItem")


def _scheme(value, default=None):
    """sanscript scheme name of a SanscriptScheme argument (None -> default)."""
    value = value or default
    return value.value if value is not None else None


def parser_field(name, bindable=query):
    """Register a resolver and report bad input as a plain GraphQL error."""
    def decorator(fn):
        @wraps(fn)
        def resolver(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except service.InputError as e:
                raise GraphQLError(str(e)) from None
        return bindable.field(name)(resolver)
    return decorator


@parser_field("splits")
def res_q_splits(_, info, text, schemeFrom=None, schemeTo=None, strictIO=False, limit=10):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    splits = service.split(text, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI), bool(strictIO), limit)
    return [[service.from_slp1(w, scheme_to, denormalize=not strictIO) for w in s] for s in splits]


@parser_field("splitPairs")
def res_q_split_pairs(_, info, text, schemeFrom=None, schemeTo=None, strictIO=False,
                      position=None, validOnly=False):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    pairs = service.split_pairs(text, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI), bool(strictIO),
                                position, bool(validOnly))
    seen, result = set(), []
    for left, right, valid in pairs:
        item = (service.from_slp1(left, scheme_to, denormalize=not strictIO),
                service.from_slp1(right, scheme_to, denormalize=not strictIO))
        if item not in seen:  # `tas` and `tar` both display as `taH`
            seen.add(item)
            result.append({'left': item[0], 'right': item[1], 'valid': valid})
    return result


@parser_field("joins")
def res_q_joins(_, info, words, schemeFrom=None, schemeTo=None, strictIO=False):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    joined = service.join(words, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI), bool(strictIO))
    shown = [service.from_slp1(j, scheme_to, denormalize=not strictIO) for j in joined]
    return list(dict.fromkeys(shown))


@parser_field("tags")
def res_q_tags(_, info, text, schemeFrom=None, schemeTo=None, strictIO=False, lexicon='COMBINED'):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    analysed = service.tags(text, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI), bool(strictIO),
                            lexicon or 'COMBINED')
    return [{
        'form': service.from_slp1(form, scheme_to, denormalize=not strictIO),
        'word': service.from_slp1(root, scheme_to),
        'tags': [service.from_slp1(t, scheme_to) for t in tagset],
    } for form, analyses in analysed for root, tagset in analyses]


@parser_field("presegmented")
def res_q_presegmented(_, info, text, schemeFrom=None, schemeTo=None, strictIO=False, limit=None):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    padas = service.presegment(text, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI), bool(strictIO))
    return [service.from_slp1(p, scheme_to, denormalize=not strictIO) for p in padas]


@parser_field("parse")
def res_q_parse(_, info, text, schemeFrom=None, schemeTo=None, strictIO=False, limit=10,
                preSegmented=False, parseLimit=2, minCostOnly=False):
    return service.parse(
        text, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI), _scheme(schemeTo, SanscriptScheme.SLP1),
        strict=bool(strictIO), limit=limit, pre_segmented=bool(preSegmented),
        parse_limit=parseLimit, min_cost_only=bool(minCostOnly))


# `Parse` and `ParseItem` values are service.SplitAnalysis / service.ParseResult
# objects; fields without a resolver here are read as attributes.

@parser_field("splitDot", parseType)
def res_parse_split_dot(split, info, scheme=None):
    return split.split_dot(_scheme(scheme))


@parser_field("splitDotURL", parseType)
def res_parse_split_dot_url(split, info, scheme=None):
    return split.split_dot_url(_scheme(scheme))


@parser_field("parseDots", parseType)
def res_parse_parse_dots(split, info, scheme=None):
    return split.parse_dots(_scheme(scheme))


@parser_field("parseDotURLs", parseType)
def res_parse_parse_dot_urls(split, info, scheme=None):
    return split.parse_dot_urls(_scheme(scheme))


@parser_field("dot", parseItemType)
def res_parse_item_dot(item, info, scheme=None):
    return item.dot(_scheme(scheme))


@parser_field("dotURL", parseItemType)
def res_parse_item_dot_url(item, info, scheme=None):
    return item.dot_url(_scheme(scheme))


@parser_field("dhatus")
def res_q_dhatus(_, info, dhatu, schemeFrom=None, schemeTo=None):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    rows = service.dhatus(dhatu, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI))
    return [{k: service.from_slp1(v, scheme_to) if isinstance(v, str) else v for k, v in row.items()}
            for row in rows]


@parser_field("maheshvaraSutras")
def res_q_maheshvara_sutras(_, info, schemeTo=None):
    scheme_to = _scheme(schemeTo, SanscriptScheme.DEVANAGARI)
    return [service.from_slp1(s, scheme_to) for s in service.maheshvara_sutras()]


@parser_field("pratyahara")
def res_q_pratyahara(_, info, name, schemeFrom=None, schemeTo=None, longForm=True, withLongVowels=False):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    key, varnas = service.pratyahara(name, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI),
                                     long_form=longForm is not False, with_long_vowels=bool(withLongVowels))
    return {'name': service.from_slp1(key, scheme_to),
            'varnas': [service.from_slp1(v, scheme_to) for v in varnas]}


@parser_field("meter")
def res_q_meter(_, info, text, schemeFrom=None, schemeTo=None):
    scheme_to = _scheme(schemeTo, SanscriptScheme.SLP1)
    lines = service.meter(text, _scheme(schemeFrom, SanscriptScheme.DEVANAGARI))
    return [{'text': service.from_slp1(line, scheme_to), 'syllables': count, 'pattern': pattern}
            for line, count, pattern in lines]
