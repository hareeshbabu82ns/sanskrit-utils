"""What this API relies on in the pinned sanskrit_parser, tested directly.

These run against the library, not our service, so that a bump of the pinned
commit in requirements.txt shows what changed underneath us. Tests marked
xfail(strict=True) describe upstream bugs that parser_service works around:
when one starts passing, the bug is fixed upstream and pytest reports it, which
is the cue to drop the workaround named in its reason.
"""
import json

import pytest
from indic_transliteration import sanscript

from sanskrit_parser import Parser, __version__
from sanskrit_parser.api import JSONEncoder
from sanskrit_parser.base.maheshvara_sutra import MaheshvaraSutras
from sanskrit_parser.base.sanskrit_base import (SanskritImmutableString,
                                                SanskritNormalizedString,
                                                SanskritObject, SanskritString,
                                                outputctx)
from sanskrit_parser.parser.datastructures import SandhiGraph, VakyaGraph
from sanskrit_parser.parser.sandhi import Sandhi
from sanskrit_parser.util import normalization
from sanskrit_parser.util.DhatuWrapper import DhatuWrapper
from sanskrit_parser.util.inriaxmlwrapper import InriaXMLWrapper
from sanskrit_parser.util.lexical_lookup_factory import (CombinedWrapper,
                                                         LexicalLookupFactory)
from sanskrit_parser.util.lexical_scorer import Scorer
from sanskrit_parser.util.sanskrit_data_wrapper import SanskritDataWrapper

SLP1 = sanscript.SLP1


def S(text):
    return SanskritImmutableString(text, encoding=SLP1)


def plain(tags):
    """[(root, tagset)] -> {(root, frozenset of tag strings)}."""
    return {(str(root), frozenset(str(t) for t in tagset)) for root, tagset in tags}


@pytest.fixture(scope='module')
def analyzer(service):
    return service.analyzer  # the lexicons are loaded once per process


@pytest.fixture(scope='module')
def parser():
    return Parser(input_encoding=SLP1, output_encoding=SLP1)


def test_version_is_the_pinned_one():
    assert __version__ == '0.2.6'


# --- base: strings, encodings, normalisation -------------------------------

def test_sanskrit_string_transcodes():
    s = SanskritString('देवदत्तः', encoding=sanscript.DEVANAGARI)
    assert s.canonical() == 'devadattaH'
    assert s.transcoded(sanscript.IAST) == 'devadattaḥ'
    assert s.devanagari() == 'देवदत्तः'
    assert str(s) == 'devadattaH' and len(s) == 10 and s[0] == 'd'


def test_sanskrit_string_detects_the_encoding():
    assert SanskritString('देव').canonical() == 'deva'
    assert SanskritString('śiva').canonical() == 'Siva'


def test_immutable_strings_compare_by_value():
    assert S('deva') == S('deva') and S('deva') != S('devI')
    assert len({S('deva'), S('deva'), S('devI')}) == 2


def test_normalized_string_non_strict():
    assert SanskritNormalizedString('rAmaH', encoding=SLP1, strict_io=False).canonical() == 'rAmas'
    assert SanskritNormalizedString('rAmaH, 12', encoding=SLP1, strict_io=False,
                                    replace_ending_visarga=None).canonical() == 'rAmaH '
    assert SanskritNormalizedString('aMgam', encoding=SLP1, strict_io=False).canonical() == 'aNgam'
    assert SanskritNormalizedString('rAmaH', encoding=SLP1, strict_io=False,
                                    replace_ending_visarga='r').canonical() == 'rAmar'
    assert SanskritNormalizedString('rAmaH', encoding=SLP1, strict_io=False,
                                    replace_ending_visarga=None).canonical() == 'rAmaH'
    assert SanskritNormalizedString('rAmaH', encoding=SLP1, strict_io=True).canonical() == 'rAmaH'


def test_sanskrit_object_carries_tags():
    o = SanskritObject('rAmas', encoding=SLP1)
    assert o.getMorphologicalTags() == []
    o.setMorphologicalTags(['a'])
    assert o.getMorphologicalTags() == ['a']


def test_output_is_denormalized_unless_strict():
    assert S('rAmas').transcoded(SLP1, strict_io=False) == 'rAmaH'
    assert S('rAmas').transcoded(SLP1, strict_io=True) == 'rAmas'
    with outputctx(strict_io=False):
        assert str(SanskritString('punar', encoding=SLP1)) == 'punaH'


def test_normalization_functions():
    assert normalization.normalize('rAmaH, gacCati! 12') == 'rAmaH gacCati '
    assert normalization.normalize('vanaM') == 'vanam'
    assert normalization.normalize('rAmo') == 'rAmaH'
    assert normalization.normalize('rAma:') == 'rAmaH'
    assert normalization.replace_ending_visarga_s('rAmaH') == 'rAmas'
    assert normalization.replace_ending_visarga_r('punaH') == 'punar'
    assert normalization.denormalize('rAmas gacCati punar') == 'rAmaH gacCati punaH'


def test_normalize_cannot_take_text_that_is_all_punctuation():
    """parser_service.normalize catches this and reports empty input."""
    with pytest.raises(IndexError):
        normalization.normalize('...')


@pytest.mark.xfail(strict=True, reason='upstream: non-strict input turns saMyoga into say~yoga, '
                                       'which the lexicon lacks; see parser_service._class_nasals')
def test_non_strict_input_keeps_anusvara_before_a_semivowel(analyzer):
    word = SanskritObject('saMyogaH', encoding=SLP1, strict_io=False)
    assert analyzer.getMorphologicalTags(word) is not None


# --- Maheshvara sutras ------------------------------------------------------

def test_maheshvara_sutras():
    ms = MaheshvaraSutras()
    assert str(ms).split()[0] == 'aiuR' and len(str(ms).split()) == 14
    assert str(ms.getPratyahara(S('jaS'))) == 'jabagaqada'
    assert str(ms.getPratyahara(S('jaS'), remove_a=True)) == 'jbgqd'
    assert str(ms.getPratyahara(S('ac'))) == 'aiufxeoEO'
    assert str(ms.getPratyahara(S('aR'), longp=False)) == 'aiu'
    assert str(ms.getPratyahara(S('ik'), dirghas=True)) == 'iIuUfFxX'
    assert ms.isInPratyahara(S('jaS'), S('g')) and not ms.isInPratyahara(S('jaS'), S('k'))
    assert ms.isInPratyahara(S('ac'), S('A'))
    assert ms.isSavarna(S('a'), S('A')) and not ms.isSavarna(S('k'), S('g'))
    assert ms.isSavarna(S('ku'), S('g')) and ms.isSavarna(S('at'), S('a')) and not ms.isSavarna(S('at'), S('A'))
    with pytest.raises(ValueError):
        ms.getPratyahara(S('kaR'))


# --- sandhi rules -----------------------------------------------------------

def test_sandhi_join():
    sandhi = Sandhi()
    assert sandhi.join(S('te'), S('eva')) == {'teeva', 'taeva', 'ta eva', 'tayeva'}
    assert sandhi.join(S('tasmin'), S('iti')) == {'tasminiti', 'tasminniti'}
    assert 'rAmo gacCati' in sandhi.join(S('rAmas'), S('gacCati'))


def test_sandhi_split():
    sandhi = Sandhi()
    assert ('tasmin', 'niti') in sandhi.split_at(S('tasminniti'), 5)
    assert sandhi.split_at(S('tasminniti'), 0) == {('t', 'asminniti')}
    assert sandhi.split_at(S('tasminniti'), 99) is None
    everything = sandhi.split_all(S('tasminniti'))
    assert ('tasmin', 'iti') in everything and ('tasminniti', '') in everything
    assert sandhi.split_at(S('taeva'), 1) == {('ta', 'eva'), ('tas', 'eva'), ('tar', 'eva'), ('taH', 'eva')}
    assert sandhi.split_all(S('taeva'), start=1, stop=2) == sandhi.split_at(S('taeva'), 1)


# --- lexical lookup ---------------------------------------------------------

def test_inria_lookup(analyzer):
    inria = analyzer.forms.inria
    assert isinstance(inria, InriaXMLWrapper)
    assert inria.valid('gacCati') and not inria.valid('xyzzy')
    assert ('gam', frozenset({'law', 'kartari', 'parasmEpadam', 'praTamapuruzaH', 'ekavacanam', 'prATamikaH'})) \
        in plain(inria.get_tags('gacCati'))
    assert inria.get_tags('xyzzy') is None
    raw = dict(inria.get_tags('gacCati', tmap=False)[::-1])   # INRIA's own abbreviations
    assert {'v', 'pr', 'trd', 'sg', 'para'} <= raw['gam']
    assert {'ppr', 'loc', 'sg'} <= raw['gacCat']


def test_sanskrit_data_lookup(analyzer):
    data = analyzer.forms.sanskrit_data
    assert isinstance(data, SanskritDataWrapper)
    assert data.valid('devasya') and not data.valid('xyzzy')
    assert plain(data.get_tags('devasya')) == {
        ('deva', frozenset({'zazWIviBaktiH', 'ekavacanam', 'puMlliNgam'})),
        ('deva', frozenset({'zazWIviBaktiH', 'ekavacanam', 'napuMsakaliNgam'})),
    }
    assert ('gam', frozenset({'ktvA'})) in plain(data.get_tags('gatvA'))
    assert ('gam', frozenset({'tumun'})) in plain(data.get_tags('gantum'))
    assert ('ca', frozenset({'avyayam'})) in plain(data.get_tags('ca'))
    assert ('gam', frozenset({'law', 'parasmEpadam', 'praTamapuruzaH', 'ekavacanam'})) in plain(data.get_tags('gacCati'))
    assert data.get_tags('xyzzy') is None


def test_combined_lookup_merges_both(analyzer):
    combined = analyzer.forms
    assert isinstance(combined, CombinedWrapper)
    merged = plain(combined.get_tags('gacCati'))
    assert merged >= plain(combined.inria.get_tags('gacCati'))
    assert {r for r, _ in merged} == {'gam', 'gacCat'}
    assert combined.valid('devasya') and not combined.valid('xyzzy')
    assert combined.get_tags('xyzzy') is None


def test_lookup_factory_rejects_unknown_names():
    with pytest.raises(Exception):
        LexicalLookupFactory.create('nonesuch')


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason='upstream: unmapped tags cannot be merged; the API does not offer them')
def test_combined_lookup_raw_tags(analyzer):
    analyzer.forms.get_tags('gacCati', tmap=False)


# --- analyzer: tags and splits ----------------------------------------------

def test_morphological_tags(analyzer):
    tags = plain(analyzer.getMorphologicalTags(SanskritObject('hares', encoding=SLP1)))
    assert ('hari#1', frozenset({'zazWIviBaktiH', 'ekavacanam', 'puMlliNgam'})) in tags
    assert analyzer.getMorphologicalTags(SanskritObject('xyzzy', encoding=SLP1)) is None


def test_has_tag(analyzer):
    word = SanskritObject('hares', encoding=SLP1)
    genitive = {S('zazWIviBaktiH')}
    assert all(genitive <= t for _, t in analyzer.hasTag(word, None, genitive))
    assert {str(r) for r, _ in analyzer.hasTag(word, S('hari#1'), None)} == {'hari#1'}
    assert analyzer.hasTag(word, S('rAma'), None) is None
    assert analyzer.hasTag(SanskritObject('xyzzy', encoding=SLP1), S('x'), None) is None


def test_sandhi_splits(analyzer):
    graph = analyzer.getSandhiSplits(SanskritObject('astyuttarasyAMdiSi', encoding=SLP1))
    assert isinstance(graph, SandhiGraph)
    splits = [[str(w) for w in s] for s in graph.find_all_paths(max_paths=5)]
    assert splits[0] == ['asti', 'uttarasyAm', 'diSi']
    assert [len(s) for s in splits] == sorted(len(s) for s in splits)
    unscored = list(analyzer.getSandhiSplits(SanskritObject('tasminniti', encoding=SLP1)).find_all_paths(score=False))
    assert [[str(w) for w in s] for s in unscored] == [['tasmin', 'iti']]
    assert analyzer.getSandhiSplits(SanskritObject('xyzqq', encoding=SLP1)) is None


def test_sandhi_split_graph_can_be_tagged(analyzer):
    graph = analyzer.getSandhiSplits(SanskritObject('tasminniti', encoding=SLP1), tag=True)
    words = [n for n in graph if isinstance(n, SanskritObject)]
    assert words and all(w.getMorphologicalTags() for w in words)


def test_presegmented_graph_is_one_path(analyzer):
    words = [SanskritObject(w, encoding=SLP1) for w in ('devadattas', 'grAmam', 'gacCati')]
    graph = analyzer.getSandhiSplits(words, pre_segmented=True)
    assert [[str(w) for w in p] for p in graph.find_all_paths()] == [['devadattas', 'grAmam', 'gacCati']]


def test_scorer_prefers_real_sentences():
    good, bad = Scorer().score_strings(['devadattas grAmam gacCati', 'de va dat tas grA mam ga cCa ti'])
    assert good > bad


# --- Parser API -------------------------------------------------------------

def test_parser_split(parser):
    splits = parser.split('astyuttarasyAMdiSi', limit=3)
    assert str(splits[0]) == "['asti', 'uttarasyAm', 'diSi']"
    assert len(splits) == 3
    assert [str(w) for w in splits[0].split] == ['asti', 'uttarasyAm', 'diSi']


def test_parser_split_without_result_warns(parser):
    with pytest.warns(UserWarning, match='No splits found'):
        assert parser.split('xyzqq') is None


def test_parser_output_encoding():
    parser = Parser(input_encoding=sanscript.DEVANAGARI, output_encoding=sanscript.IAST)
    (split,) = parser.split('तस्मिन्निति', limit=1)
    assert str(split) == "['tasmin', 'iti']"


def test_parser_presegmented_and_parse(parser):
    (split,) = parser.split('devadattaH grAmaM gacCati', pre_segmented=True)
    assert str(split) == "['devadattaH', 'grAmam', 'gacCati']"
    parses = split.parse(limit=5)
    assert parses and [p.cost for p in parses] == sorted(p.cost for p in parses)
    best = parses[0]
    lines = str(best).split('\n')
    assert lines[0].startswith('devadattaH => (devadatta, [') and lines[0].endswith(': kartA of gacCati')
    assert lines[1].endswith(': karma of gacCati')
    assert lines[2].startswith('gacCati => (gam, [')

    rows = best.to_conll()
    assert [r[:4] + r[5:] for r in rows] == [['1', 'devadattaH', '_', 'devadatta', '3', 'kartA'],
                                             ['2', 'grAmam', '_', 'grAma', '3', 'karma'],
                                             ['3', 'gacCati', '_', 'gam', '0', 'root']]
    graph = best.serializable()['graph']
    assert graph[0]['sambandha'] == 'kartA' and graph[0]['predecessor']['pada'] == 'gacCati'
    assert set(graph[2]) == {'pada', 'root', 'tags'}        # the root of the tree has no edge
    assert 'kartA' in best.to_dot() and best.to_dot().startswith('digraph')
    assert split.to_dot().count('->') > best.to_dot().count('->')
    assert json.loads(json.dumps(best, cls=JSONEncoder))['graph'] == graph


def test_parser_min_cost_only(parser):
    # a fresh split each time: parsing one twice changes it (see the xfail below)
    everything = parser.split('devadattaH grAmaM gacCati', pre_segmented=True)[0].parse(limit=50)
    cheapest = parser.split('devadattaH grAmaM gacCati', pre_segmented=True)[0].parse(limit=50, min_cost_only=True)
    assert {p.cost for p in cheapest} == {everything[0].cost}
    assert len(cheapest) == sum(p.cost == everything[0].cost for p in everything)


def test_vakya_graph_directly(analyzer):
    words = []
    for w in ('devadattas', 'grAmam', 'gacCati'):
        o = SanskritObject(w, encoding=SLP1)
        o.setMorphologicalTags(analyzer.getMorphologicalTags(o))
        words.append(o)
    graph = VakyaGraph(words, max_parse_dc=5)
    assert graph.parses and len(graph.parses) == len(graph.parse_costs)
    labels = {label for _, _, label in graph.parses[0].edges(data='label')}
    assert labels == {'kartA', 'karma'}
    assert {n.index for n in graph.G} == {0, 1, 2}


@pytest.mark.xfail(strict=True, reason='upstream: splits share word objects and Split.parse appends '
                                       'tags to them each time; see parser_service.SplitAnalysis')
def test_parsing_one_split_leaves_the_others_alone(parser):
    first, second = parser.split('devadattaH grAmaM gacCati', limit=2)
    shared = next(w for w in first.split for v in second.split if w is v)
    first.parse(limit=1)
    count = len(shared.getMorphologicalTags())
    second.parse(limit=1)
    assert len(shared.getMorphologicalTags()) == count


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason='upstream: an unknown word in a pre-segmented sentence is not handled; '
                          'see parser_service.presegment')
@pytest.mark.filterwarnings('ignore:No splits found')
def test_parser_presegmented_unknown_word(parser):
    parser.split('devadattaH xyzzyq gacCati', pre_segmented=True)


@pytest.mark.xfail(strict=True, raises=FileNotFoundError,
                   reason='upstream: the pada generator needs sutra files the package does not '
                          'ship, so the API has no prakriya query')
def test_generator_data_is_packaged():
    from sanskrit_parser.generator.sutras_yaml import SutraFactory
    SutraFactory()


# --- dhatupatha -------------------------------------------------------------

def test_dhatu_wrapper():
    dhatus = DhatuWrapper()
    assert dhatus.is_sakarmaka('gam') and not dhatus.is_dvikarmaka('gam')
    assert dhatus.is_dvikarmaka('nI')
    assert not dhatus.is_sakarmaka('zzz')
    (gam,) = dhatus._get_dhatus('gam')
    assert gam['mUlaDAtuH'] == 'gamlf' and gam['gaRaH'] == 'BvAdiH' and gam['rUpam'] == 'gacCati'
    assert set(gam) == {'DAtuH', 'mUlaDAtuH', 'DAtvarTaH', 'gaRaH', 'karmakatvaM', 'iwtvaM', 'upagrahaH', 'rUpam'}
