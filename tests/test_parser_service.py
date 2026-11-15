"""parser_service: the parts a GraphQL query cannot reach or pin down."""
import threading
import time

import pytest
from indic_transliteration import sanscript

SLP1 = sanscript.SLP1
LONG_SENTENCE = 'rAmaH sItayA saha vanaM gacCati tatra ca lakzmaRaH api AgacCati'


# --- normalisation ----------------------------------------------------------

@pytest.mark.parametrize('typed, read', [
    ('aMga', 'aNga'), ('paMca', 'paYca'), ('paMqita', 'paRqita'), ('kiMtu', 'kintu'),
    ('SuklAMbara', 'SuklAmbara'), ('saMmAna', 'sammAna'), ('saMnyAsa', 'sannyAsa'),
    # not before a semivowel, sibilant or h, nor across a space
    ('saMyoga', 'saMyoga'), ('saMvAda', 'saMvAda'), ('saMskfta', 'saMskfta'),
    ('siMha', 'siMha'), ('aMSa', 'aMSa'), ('ahaM karomi', 'ahaM karomi'),
])
def test_anusvara_before_a_stop_becomes_the_class_nasal(service, typed, read):
    assert service.normalize(typed, SLP1, strict=True) == read
    assert service.normalize(typed + ' ca', SLP1, strict=False) == read + ' ca'


def test_the_class_nasal_spelling_is_the_one_the_lexicon_has(service):
    for typed in ('aMgam', 'paMqitas', 'kiMtu', 'saMBavas'):
        assert not service.analyzer.forms.valid(typed)
        assert service.analyzer.forms.valid(service.normalize(typed, SLP1, strict=True))
    # and the anusvara that is kept is the spelling it has
    for kept in ('saMyogas', 'saMvAdas', 'siMhas'):
        assert service.analyzer.forms.valid(service.normalize(kept, SLP1, strict=True))


@pytest.mark.parametrize('typed, strict, read', [
    ('  rAmaH   gacCati \n', True, 'rAmaH gacCati'),
    ('rAmaH, gacCati! (1)', False, 'rAmaH gacCati'),
    ('rAmaH | gacCati ||', False, 'rAmaH gacCati'),
    ('rAmo', False, 'rAmaH'),            # a final o stands for aH
    ('rAmo', True, 'rAmo'),
    ('vanaM', False, 'vanam'),
    ('vanaM', True, 'vanaM'),
    ('rAma:', False, 'rAmaH'),           # a colon typed for visarga
])
def test_normalize(service, typed, strict, read):
    assert service.normalize(typed, SLP1, strict) == read


def test_normalize_converts_from_the_input_scheme(service):
    assert service.normalize('रामः गच्छति ।', sanscript.DEVANAGARI, strict=False) == 'rAmaH gacCati'
    assert service.normalize('rāmaḥ', sanscript.IAST, strict=True) == 'rAmaH'


@pytest.mark.parametrize('typed', ['', '   ', '...', '12 34', '।॥'])
def test_normalize_refuses_text_without_letters(service, typed):
    with pytest.raises(service.InputError, match='no Sanskrit letters'):
        service.normalize(typed, SLP1, strict=False)


def test_from_slp1_denormalize(service):
    assert service.from_slp1('rAmas', SLP1, denormalize=True) == 'rAmaH'
    assert service.from_slp1('punar', sanscript.DEVANAGARI, denormalize=True) == 'पुनः'
    assert service.from_slp1('punar', sanscript.DEVANAGARI) == 'पुनर्'


def test_unknown_scheme_is_an_input_error(service):
    with pytest.raises(service.InputError):
        service.to_slp1('x', 'english')
    with pytest.raises(service.InputError):
        service.from_slp1('x', 'klingon')


# --- splitting --------------------------------------------------------------

def test_split_returns_plain_slp1_words(service):
    assert service.split('tasminniti', SLP1, limit=1) == [['tasmin', 'iti']]


def test_limits_are_capped(service):
    assert service._check_limit(10 ** 6) == service.MAX_LIMIT
    with pytest.raises(service.InputError):
        service._check_limit(None)


def test_join_results_are_capped(service, monkeypatch):
    monkeypatch.setattr(service, 'MAX_JOIN_RESULTS', 3)
    words = ['asti', 'uttarasyAm', 'diSi', 'devatA', 'AtmA']
    assert len(service.join(words, SLP1)) == 3


def test_concurrent_requests_do_not_disturb_each_other(service):
    """The analyzer keeps the state of a split on itself; the service locks it."""
    texts = ['astyuttarasyAMdiSidevatAtmA', 'tasminniti', 'rAmaH vanaM gacCati',
             'devadattaH grAmaM gacCati']
    expected = {t: service.split(t, SLP1, limit=5) for t in texts}
    failures = []

    def worker(text):
        for _ in range(15):
            if service.split(text, SLP1, limit=5) != expected[text]:
                failures.append(text)

    threads = [threading.Thread(target=worker, args=(t,)) for t in texts * 2]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not failures


def test_requests_carry_their_own_settings(service):
    """Nothing about one call's schemes or strictness is left behind for the next."""
    def run(scheme, strict):
        return service.parse('devadattaH grAmaM gacCati', SLP1, scheme, strict=strict, limit=1)[0]

    a, b = run(sanscript.TELUGU, False), run(SLP1, True)
    assert a.split == ['దేవదత్తః', 'గ్రామమ్', 'గచ్ఛతి']
    assert b.split == ['devadattas', 'grAmam', 'gacCati']
    assert a.analysis[0].graph[0]['node']['pada'] == 'దేవదత్తః'
    assert b.analysis[0].graph[0]['node']['pada'] == 'devadattas'


# --- vakya analysis: laziness and the time budget ---------------------------

def test_analysis_is_not_run_until_it_is_asked_for(service, monkeypatch):
    calls = []
    original = service._BudgetedVakyaGraph.__init__

    def counting(self, *args, **kwargs):
        calls.append(1)
        original(self, *args, **kwargs)

    monkeypatch.setattr(service._BudgetedVakyaGraph, '__init__', counting)
    results = service.parse('devadattaH grAmaM gacCati', SLP1, SLP1, limit=3)
    assert [r.split for r in results] and not calls
    assert results[0].status == 'OK' and len(calls) == 1
    # every other field of that split reuses the one analysis
    results[0].analysis, results[0].split_dot(), results[0].parse_dots(sanscript.IAST)
    assert len(calls) == 1


def test_a_split_that_runs_out_of_time_is_cut_off(service):
    budget = service.ParseBudget(per_split=0.3, total=30)
    (result,) = service.parse(LONG_SENTENCE, SLP1, SLP1, limit=1, budget=budget)
    started = time.monotonic()
    assert result.status == 'TIMEOUT'
    assert time.monotonic() - started < 3
    assert result.analysis == [] and result.parse_dots() == []
    # the relations that were found before the search began are still there
    assert result.split_dot().startswith('digraph {') and '->' in result.split_dot()


def test_the_whole_query_has_a_budget_too(service):
    budget = service.ParseBudget(per_split=0.2, total=0.3)
    results = service.parse(LONG_SENTENCE, SLP1, SLP1, limit=4, budget=budget)
    started = time.monotonic()
    assert [r.status for r in results] == ['TIMEOUT'] * 4
    assert time.monotonic() - started < 3
    # the later splits were never searched, but their possible relations are still given
    assert results[-1]._analysed[0] is results[-1]._unsearched
    assert results[-1].split_dot().startswith('digraph {') and results[-1].relations()


def test_relations_do_not_start_the_search(service, monkeypatch):
    """splitDot and analysisSplitDot on their own stay quick for a sentence the search cannot finish."""
    searched = []
    original = service.VakyaGraph.get_parses_dc
    monkeypatch.setattr(service.VakyaGraph, 'get_parses_dc',
                        lambda self: searched.append(1) or original(self))
    (result,) = service.parse(LONG_SENTENCE, SLP1, SLP1, limit=1,
                              budget=service.ParseBudget(per_split=0.3, total=0.3))
    started = time.monotonic()
    rows, dot = result.relations(), result.split_dot()
    assert rows and '->' in dot
    assert not searched and time.monotonic() - started < 1
    # asking for the analyses afterwards does search, and the relations stay the same
    assert result.status == 'TIMEOUT' and searched
    assert result.relations() == rows and result.split_dot() == dot


def test_a_short_sentence_is_not_affected_by_the_budget(service):
    budget = service.ParseBudget(per_split=5, total=5)
    results = service.parse('devadattaH grAmaM gacCati', SLP1, SLP1, limit=3, budget=budget)
    assert [r.status for r in results] == ['OK'] * 3


def test_budget_defaults_come_from_the_environment_settings(service):
    budget = service.ParseBudget()
    assert (budget.per_split, budget.total) == (service.PARSE_SPLIT_TIMEOUT, service.PARSE_TOTAL_TIMEOUT)
    assert budget.per_split <= budget.total


def test_a_word_without_tags_gives_no_parse_instead_of_an_error(service):
    out = service._Output(SLP1, True)
    result = service.SplitAnalysis(['rAmas', 'xyzzyq'], out, service.ParseBudget())
    assert result.status == 'NO_PARSE' and result.analysis == [] and result.split_dot() == ''


# --- dhatupatha lookup -------------------------------------------------------

@pytest.mark.parametrize('root, found_as, takes_object', [
    ('gam', ['gam'], True),
    ('sTA', ['sTA'], False),
    ('DyA', ['DyE'], True),          # the lexicon's name for a root in -ai
    ('mlA', ['mlE'], False),
    ('SA', ['SE', 'So'], True),      # ... or in -o: both are candidates
    ('stu', [], False),              # not in the dhatupatha: no object unless asked
])
def test_dhatupatha_finds_roots_by_the_lexicon_name(service, root, found_as, takes_object):
    assert [e['DAtuH'] for e in service.dhatupatha._get_dhatus(root)] == found_as
    assert service.dhatupatha.is_sakarmaka(root) is takes_object


def test_dhatupatha_unknown_roots_transitive_is_scoped(service):
    patha = service.dhatupatha
    with patha.unknown_roots_transitive(True):
        assert patha.is_sakarmaka('stu') and patha.is_sakarmaka('zzz')
        assert not patha.is_sakarmaka('sTA')         # a root that is found keeps its own answer
        with patha.unknown_roots_transitive(False):
            assert not patha.is_sakarmaka('stu')
        assert patha.is_sakarmaka('stu')
    assert not patha.is_sakarmaka('stu')


def test_dhatupatha_setting_does_not_cross_threads(service):
    """One request asking for it must not switch it on for another."""
    seen = []
    with service.dhatupatha.unknown_roots_transitive(True):
        t = threading.Thread(target=lambda: seen.append(service.dhatupatha.is_sakarmaka('stu')))
        t.start()
        t.join()
    assert seen == [False]


def test_relations_can_leave_the_head_out(service):
    (result,) = service.parse('devadattaH grAmaM gacCati', SLP1, SLP1, limit=1)
    by_head, by_word = result.relations(), result.relations(by_head=False)
    assert len(by_word) < len(by_head)
    assert all(r['predecessor'] is None for r in by_word)
    assert {(r['node']['pada'], r['node']['root'], r['sambandha']) for r in by_head} == \
           {(r['node']['pada'], r['node']['root'], r['sambandha']) for r in by_word}


def test_dhatupatha_double_object_roots(service):
    assert service.dhatupatha.is_dvikarmaka('nI')
    assert not service.dhatupatha.is_dvikarmaka('gam') and not service.dhatupatha.is_dvikarmaka('stu')


def test_the_parser_uses_this_dhatupatha(service):
    from sanskrit_parser.parser import datastructures
    assert datastructures.dw is service.dhatupatha


def test_dot_escapes_quotes_and_backslashes(service):
    assert service._dot_quote('a"b\\c') == '"a\\"b\\\\c"'


def test_dot_url_is_built_not_fetched(service):
    assert service.dot_url('digraph {}') == 'https://image-charts.com/chart?cht=gv%3Adot&chl=digraph+%7B%7D'


def test_splits_are_the_same_on_every_call(service):
    """Upstream's ranking picks its candidates arbitrarily among equally short splits."""
    first = service.split('astyuttarasyAMdiSidevatAtmA', SLP1, limit=5)
    assert len(first) == 5
    for _ in range(8):
        assert service.split('astyuttarasyAMdiSidevatAtmA', SLP1, limit=5) == first


def test_a_smaller_limit_returns_a_prefix_of_a_larger_one(service):
    ten = service.split('astyuttarasyAMdiSidevatAtmA', SLP1, limit=10)
    for limit in (1, 3, 5):
        assert service.split('astyuttarasyAMdiSidevatAtmA', SLP1, limit=limit) == ten[:limit]


def test_splits_prefer_fewer_words(service):
    lengths = [len(s) for s in service.split('astyuttarasyAMdiSidevatAtmA', SLP1, limit=10)]
    assert lengths == sorted(lengths)
