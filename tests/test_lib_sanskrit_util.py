"""sanskrit_util (the `sanskrit-util` package), tested directly.

sanskrit_parser uses it for one of its two lexicons (SanskritDataWrapper ->
SimpleAnalyzer); the API also uses `sounds.meter`. The rest of the package is
covered here so that it is known what works. Tests marked xfail(strict=True)
describe bugs in the released package; they are the reason the API has no
declension, conjugation or tagger queries built on it.
"""
import pytest

import sanskrit_util
from sanskrit_parser.util.data_manager import data_file_path
from sanskrit_util import analyze, generate, models, query, sandhi, schema, sounds, tagger, util


@pytest.fixture(scope='module')
def ctx():
    """A context on the database that ships with sanskrit_parser."""
    return sanskrit_util.Context({
        'DATABASE_URI': 'sqlite:///' + data_file_path('sanskrit_data.db'),
        'DATA_PATH': ''})


@pytest.fixture(scope='module')
def analyzer(ctx):
    return analyze.SimpleAnalyzer(ctx)


@pytest.fixture(scope='module')
def simple_query(ctx):
    return query.SimpleQuery(ctx)


@pytest.fixture(scope='module')
def sandhi_rules(ctx):
    rules = [(r.first, r.second, r.result) for r in ctx.session.query(schema.SandhiRule).all()]
    ctx.session.remove()
    return rules


# --- context ----------------------------------------------------------------

def test_context_config_and_enums(ctx):
    assert ctx.config['DATABASE_URI'].endswith('sanskrit_data.db')
    assert ctx.config['NOMINAL_STEMS'] == 'nominal-stems.csv'   # defaults are filled in
    assert ctx.enum_id['gender']['m'] == ctx.enum_id['gender']['masculine'] == 1
    assert ctx.enum_id['case']['6'] == 6 and ctx.enum_abbr['case'][6] == '6'
    assert ctx.enum_abbr['number'][1] == 's' and ctx.enum_abbr['person'][3] == '3'
    assert ctx.enum_id['mode']['pres'] == 1 and ctx.enum_id['voice']['para'] == 1
    assert ctx.gender_set[7] == {1, 2, 3}    # the "any gender" group
    assert set(ctx.enum_id) >= {'case', 'gender', 'mode', 'number', 'person', 'vclass', 'voice'}


def test_context_ignores_lowercase_keys_and_can_stay_unconnected():
    ctx = sanskrit_util.Context({'DATA_PATH': '/data', 'scratch': 1}, connect=False)
    assert 'scratch' not in ctx.config and ctx.session is None
    assert ctx.config['VERBS'] == '/data/verbs.csv'


# --- analyzer ---------------------------------------------------------------

def _forms(ctx, results):
    """Analysis results as comparable tuples."""
    out = set()
    for r in results:
        r = ctx.session.merge(r) if getattr(r, 'id', None) else r
        kind = type(r).__name__
        if kind == 'Nominal':
            out.add((kind, r.stem.name, r.gender_id, r.case_id, r.number_id, bool(r.compounded)))
        elif kind == 'Verb':
            out.add((kind, r.root.name, r.person_id, r.number_id, r.mode_id, r.voice_id))
        elif kind in ('Gerund', 'Infinitive'):
            out.add((kind, r.root.name))
        else:
            out.add((kind, r.name))
    ctx.session.remove()
    return out


def test_analyze_a_verb(ctx, analyzer):
    assert ('Verb', 'gam', 3, 1, 1, 1) in _forms(ctx, analyzer.analyze('gacCati'))   # 3rd sg present parasmaipada


def test_analyze_a_noun_by_stem_and_ending(ctx, analyzer):
    assert _forms(ctx, analyzer.analyze('devasya')) == {
        ('Nominal', 'deva', 1, 6, 1, False), ('Nominal', 'deva', 3, 6, 1, False)}


def test_analyze_a_stored_pronoun_form(ctx, analyzer):
    assert _forms(ctx, analyzer.analyze('tasmin')) == {
        ('Nominal', 'tad', 1, 7, 1, False), ('Nominal', 'tad', 3, 7, 1, False)}


def test_analyze_indeclinables(ctx, analyzer):
    assert _forms(ctx, analyzer.analyze('gatvA')) == {('Gerund', 'gam')}
    assert ('Infinitive', 'gam') in _forms(ctx, analyzer.analyze('gantum'))
    assert ('Indeclinable', 'ca') in _forms(ctx, analyzer.analyze('ca'))


def test_analyze_a_compound_first_member(ctx, analyzer):
    assert ('Nominal', 'deva', 1, None, None, True) in _forms(ctx, analyzer.analyze('deva'))


def test_analyze_an_unknown_word(analyzer):
    assert analyzer.analyze('xyzzy') == []


# --- query and generate -----------------------------------------------------

DEVA = {
    '1': 'devaH devO devAH', '2': 'devam devO devAn', '3': 'devena devAByAm devEH',
    '4': 'devAya devAByAm deveByaH', '5': 'devAt devAByAm deveByaH',
    '6': 'devasya devayoH devAnAm', '7': 'deve devayoH devezu', '8': 'deva devO devAH',
}


def _table(paradigm):
    return {case: ' '.join(paradigm[(case, n)] for n in 'sdp') for case in {c for c, _ in paradigm}}


def test_noun_paradigm(simple_query):
    assert _table(simple_query.noun('deva', 'm')) == DEVA
    assert _table(simple_query.noun('vana', 'n'))['1'] == 'vanam vane vanAni'
    assert _table(simple_query.noun('ramA', 'f'))['6'] == 'ramAyAH ramayoH ramAnAm'
    assert _table(simple_query.noun('Bagavat', 'm'))['1'] == 'BagavAn BagavantO BagavantaH'
    assert simple_query.noun('xyzzy', 'm') == {}


def test_nominal_generator(ctx):
    paradigm = generate.NominalGenerator(ctx).paradigm('deva', 'm')
    assert len(paradigm) == 24
    assert paradigm[('6', 's')] == 'devasya' and paradigm[('1', 's')] == 'devas'   # before simplify()


@pytest.mark.xfail(strict=True, reason='sanskrit_util: endings of different stem classes overwrite '
                                       'each other, so many paradigms come out wrong')
@pytest.mark.parametrize('stem, gender, case, forms', [
    ('nadI', 'f', '1', 'nadI nadyO nadyaH'),
    ('mati', 'f', '3', 'matyA matiByAm matiBiH'),
    ('rAjan', 'm', '3', 'rAjYA rAjaByAm rAjaBiH'),
    ('mAtf', 'f', '1', 'mAtA mAtarO mAtaraH'),
])
def test_noun_paradigm_of_other_stem_classes(simple_query, stem, gender, case, forms):
    assert _table(simple_query.noun(stem, gender))[case] == forms


@pytest.mark.xfail(strict=True, raises=(KeyError, ValueError),
                   reason='sanskrit_util: some consonant stems have no endings to generate from')
@pytest.mark.parametrize('stem, gender', [('Atman', 'm'), ('vAc', 'f')])
def test_noun_paradigm_of_consonant_stems(simple_query, stem, gender):
    simple_query.noun(stem, gender)


def test_pronoun_paradigm(simple_query):
    tad = _table(simple_query.pronoun('tad', 'm'))
    assert tad['1'] == 'saH tO te' and tad['7'] == 'tasmin tayoH tezu'
    assert '8' not in tad                      # pronouns have no vocative
    assert _table(simple_query.pronoun('tad', 'f'))['1'] == 'sA te tAH'
    assert _table(simple_query.pronoun('asmad', 'none'))['1'] == 'aham AvAm vayam'
    assert simple_query.pronoun('xyzzy', 'm') == {}


def test_verb_forms_are_stored_for_a_root(ctx):
    """The data SimpleQuery.verb reads is sound; see the next test for the method."""
    session = ctx.session
    root = session.query(schema.Root).filter(schema.Root.name == 'gam').one()
    forms = {(v.person_id, v.number_id): v.name
             for v in session.query(schema.Verb).filter_by(root_id=root.id, mode_id=1, voice_id=1, vclass_id=1)}
    session.remove()
    assert forms[(3, 1)] == 'gacCati' and forms[(3, 3)] == 'gacCanti' and forms[(1, 1)] == 'gacCAmi'
    assert len(forms) == 9


@pytest.mark.xfail(strict=True, reason='sanskrit_util: verb() returns one form per cell and the '
                                       "root's causative and desiderative forms overwrite the plain ones")
def test_verb_paradigm(simple_query):
    assert simple_query.verb('gam', 'pres', 'para')[('3', 's')] == 'gacCati'


@pytest.mark.xfail(strict=True, raises=AttributeError,
                   reason='sanskrit_util: verb_summary() reads ParticipleStem.root_id, which the schema lacks')
def test_verb_summary(simple_query):
    simple_query.verb_summary('gam')


def test_verb_summary_of_an_unknown_root(simple_query):
    assert simple_query.verb_summary('xyzzy') == {}


# --- sounds -----------------------------------------------------------------

def test_sound_classes():
    assert sounds.VOWELS == set('aAiIuUfFxXeEoO') and sounds.SHORT_VOWELS == set('aiufx')
    assert 'k' in sounds.STOPS and 'n' in sounds.NASALS and 'y' in sounds.SEMIVOWELS
    assert sounds.CONSONANTS.isdisjoint(sounds.VOWELS)
    assert sounds.ALL_SOUNDS < sounds.ALL_TOKENS and ' ' in sounds.ALL_TOKENS


@pytest.mark.parametrize('fn, letter, result', [
    ('shorten', 'A', 'a'), ('lengthen', 'a', 'A'), ('semivowel', 'i', 'y'), ('semivowel', 'e', 'ay'),
    ('aspirate', 'k', 'K'), ('deaspirate', 'K', 'k'), ('voice', 'k', 'g'), ('devoice', 'g', 'k'),
    ('nasalize', 'k', 'N'), ('dentalize', 'w', 't'), ('retroflex', 't', 'w'),
    ('guna', 'i', 'e'), ('guna', 'f', 'ar'), ('vrddhi', 'i', 'E'), ('vrddhi', 'a', 'A'),
    ('samprasarana', 'y', 'i'), ('simplify', 'j', 'w'), ('simplify', 's', 'H'),
    ('guna', 'k', 'k'),      # a letter the change does not apply to comes back as it is
])
def test_letter_transforms(fn, letter, result):
    assert getattr(sounds, fn)(letter) == result


def test_term_simplify_reduces_the_final_consonant():
    assert sounds.Term('devas').simplify() == 'devaH'
    assert sounds.Term('marut').simplify() == 'marut'


@pytest.mark.xfail(strict=True, reason="sanskrit_util: simplify() is documented to turn 'c' into 'k' but has no rule for it")
def test_simplify_palatal():
    assert sounds.simplify('c') == 'k'


def test_clean_and_sort_key():
    assert sounds.clean('de1va!', sounds.ALL_SOUNDS) == 'deva'
    words = ['devI', 'deva', 'Atman', 'agni', 'kavi']
    assert sorted(words, key=sounds.key_fn) == ['agni', 'Atman', 'kavi', 'deva', 'devI']


def test_meter_and_syllables():
    assert sounds.num_syllables('SuklAmbaraDaraM vizRuM') == 8
    assert sounds.meter('SuklAmbaraDaraM vizRuM') == ['_', '_', '.', '.', '.', '_', '_', '_']
    assert sounds.meter('rAmaH') == ['_', '_']
    assert sounds.meter('a') == ['.']
    assert sounds.meter('satya', heavy='G', light='L') == ['G', 'L']
    assert sounds.meter('') == []


# --- sandhi -----------------------------------------------------------------

def test_sandhi_rules_are_in_the_database(sandhi_rules):
    assert len(sandhi_rules) > 500 and ('a', 'i', 'e') in sandhi_rules


def test_joiner(sandhi_rules):
    joiner = sandhi.Joiner(sandhi_rules)
    assert joiner.join(['tasya', 'icCA']) == 'tasyecCA'
    assert joiner.join(['rAmas', 'gacCati']) == 'rAmo gacCati'
    assert joiner.join(['tat', 'ca']) == 'tac ca'
    assert joiner.join(['tasya', '', 'icCA']) == 'tasyecCA'         # empty chunks are skipped
    assert joiner.join([sandhi.Exempt('te'), 'iti']) == 'te iti'    # exempt from sandhi
    assert sandhi.Joiner().join(['a', 'b']) == 'a b'                # no rules: no change


def test_internal_retroflexion():
    assert sandhi.Joiner.internal_retroflex('rAmena') == 'rAmeRa'
    assert sandhi.Joiner.internal_retroflex('nisanna') == 'nizaRRa'
    assert sandhi.Joiner.internal_retroflex('devena') == 'devena'


def test_splitter(sandhi_rules):
    splits = list(sandhi.Splitter(sandhi_rules).iter_splits('tasyecCA'))
    assert ('tasya', 'icCA') in splits
    assert ('tasy', 'ecCA') in splits          # the plain cut at every position
    assert splits[-1] == ('tasyecCA', '')      # and the word unsplit


# --- tagger, models, util ---------------------------------------------------

def test_tagger_wraps_what_it_cannot_parse(ctx):
    (item,) = tagger.Tagger(ctx).tag('xyzzy')
    assert isinstance(item.form, tagger.NonForm)
    assert item.human_readable_form(ctx) == ('xyzzy', '', '', '')
    assert item.tag(ctx) == models.SEQUENCE_BOUNDARY
    assert tagger.Tagger(ctx).tag('') is None


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason='sanskrit_util: the tagger compares its items when two states tie, '
                          'which Python 3 does not allow')
def test_tagger_tags_a_known_word(ctx):
    tagger.Tagger(ctx).tag('gacCati')


def test_sequence_model():
    model = models.SequenceModel()
    model.insert(['a', 'b', 'a', 'b'])
    assert model.joint[('a', 'b')] == 2 and model.prior['a'] == 2
    assert model.joint[(models.SEQUENCE_BOUNDARY, 'a')] == 1
    assert model.log_cond_prob(['a'], 'b') > model.log_cond_prob(['a'], 'a')


def test_hash_trie_returns_every_prefix_match():
    trie = util.HashTrie()
    trie['a'] = 1
    trie['ab'] = 2
    trie['b'] = 3
    assert trie['abc'] == {1, 2} and trie['a'] == {1} and trie['xyz'] == set()


def test_priority_queue_pops_highest_first():
    q = util.PriorityQueue()
    q.push('low', 1)
    q.push('high', 5)
    assert len(q) == 2 and q.peek() == ('high', 5)
    assert q.pop() == 'high' and q.pop_with_priority() == ('low', 1) and len(q) == 0
