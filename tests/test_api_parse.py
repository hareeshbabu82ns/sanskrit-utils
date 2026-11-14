"""GraphQL: tags and parse (vakya analysis)."""
import re

import pytest

SLP = 'schemeFrom: SLP1'
SENTENCE = 'देवदत्तः ग्रामं गच्छति'


# --- tags -----------------------------------------------------------------

def test_tags_of_a_noun(gql):
    data = gql('{ tags(text: "కాలిదాసస్య", schemeFrom: TELUGU, schemeTo: TELUGU) { form word tags } }')
    assert data['tags'] == [{'form': 'కాలిదాసస్య', 'word': 'కాలిదాస',
                             'tags': ['ఏకవచనమ్', 'పుంల్లిఙ్గమ్', 'షష్ఠీవిభక్తిః']}]


def test_tags_of_a_verb(gql):
    tags = gql('{ tags(text: "gacCati", %s) { word tags } }' % SLP)['tags']
    verb = [t for t in tags if t['word'] == 'gam' and 'law' in t['tags']]
    assert verb and {'ekavacanam', 'praTamapuruzaH', 'parasmEpadam'} <= set(verb[0]['tags'])


def test_tags_are_in_a_stable_order(gql):
    q = '{ tags(text: "hareH", %s) { word tags } }' % SLP
    first = gql(q)['tags']
    assert first == gql(q)['tags']
    assert first == sorted(first, key=lambda t: (t['word'], t['tags']))
    assert all(t['tags'] == sorted(t['tags']) for t in first)


@pytest.mark.parametrize('word, root', [('hareH', 'hari'), ('punaH', 'punar'), ('rAmaH', 'rAma')])
def test_tags_reads_a_final_visarga_as_s_or_r(gql, word, root):
    tags = gql('query($w: String!) { tags(text: $w, %s) { form word } }' % SLP, w=word)['tags']
    assert tags and {t['form'] for t in tags} == {word}
    if root != 'punar':  # punaH is also a form of pu/pU, which the s reading finds first
        assert root in {t['word'] for t in tags}


def test_tags_strict_takes_the_word_as_typed(gql):
    q = 'query($w: String!) { tags(text: $w, %s, strictIO: true) { form word } }' % SLP
    assert gql(q, w='rAmaH')['tags'] == []
    assert {'form': 'rAmas', 'word': 'rAma'} in gql(q, w='rAmas')['tags']
    assert {'form': 'punar', 'word': 'punar'} in gql(q, w='punar')['tags']


def test_tags_does_not_show_a_stem_with_visarga(gql):
    """manas is the stem; only the word form manaH ends in visarga."""
    tags = gql('{ tags(text: "manaH", %s) { form word } }' % SLP)['tags']
    assert {'form': 'manaH', 'word': 'manas'} in tags


def test_tags_of_each_word_of_a_sentence(gql):
    tags = gql('{ tags(text: "rAmaH gacCati", %s, schemeTo: IAST) { form word } }' % SLP)['tags']
    assert [t['form'] for t in tags] == sorted([t['form'] for t in tags], key=['rāmaḥ', 'gacchati'].index)
    assert {'form': 'rāmaḥ', 'word': 'rāma'} in tags
    assert {'form': 'gacchati', 'word': 'gam'} in tags


def test_tags_of_a_word_with_anusvara_before_a_semivowel(gql):
    assert gql('{ tags(text: "saMyogaH", %s) { word } }' % SLP)['tags'] == [{'word': 'saMyoga'}]


def test_tags_of_an_unknown_word_is_empty(gql):
    assert gql('{ tags(text: "xyzzy", %s) { word } }' % SLP)['tags'] == []


def test_tags_lexicon_choice(gql):
    q = '{ tags(text: "gacCati", %s, lexicon: %s) { word tags } }'
    inria = gql(q % (SLP, 'INRIA'))['tags']
    data = gql(q % (SLP, 'SANSKRIT_DATA'))['tags']
    combined = gql(q % (SLP, 'COMBINED'))['tags']
    assert inria and data and inria != data
    # only INRIA marks primary conjugation
    assert any('prATamikaH' in t['tags'] for t in inria)
    assert not any('prATamikaH' in t['tags'] for t in data)
    assert {t['word'] for t in combined} >= {t['word'] for t in inria} | {t['word'] for t in data}


# --- parse ----------------------------------------------------------------

PARSE_FIELDS = '''
  split status
  analysis { cost graph { node { index pada root tags } predecessor { index pada } sambandha } }
'''


def test_parse_reported_query_now_has_an_analysis(gql):
    """strictIO: true used to give every split an empty `analysis`."""
    data = gql('''{
      parse(text: "శుక్లాంబరధరం విష్ణుం శశివర్ణం చతుర్భుజమ్"
            schemeFrom: TELUGU schemeTo: TELUGU strictIO: true limit: 2) {
        analysis { graph { node { pada root tags } sambandha } }
        splitDot
      }
    }''')
    first = data['parse'][0]
    assert len(first['analysis']) == 2
    graph = first['analysis'][0]['graph']
    assert [g['node']['pada'] for g in graph] == ['శుక్లామ్బరధరమ్', 'విష్ణుమ్', 'శశి', 'వర్ణమ్', 'చతుర్భుజమ్']
    assert [g['node']['root'] for g in graph] == ['శుక్లామ్బరధర', 'విష్ణు', 'శశిన్', 'వర్ణ', 'చతుర్భుజ']
    assert sorted(g['sambandha'] for g in graph if g['sambandha']) == ['విశేషణమ్'] * 3 + ['సమస్త']
    assert first['splitDot'].startswith('digraph {')


def test_parse_simple_sentence(gql):
    data = gql('{ parse(text: "%s", limit: 1) { %s } }' % (SENTENCE, PARSE_FIELDS))
    (result,) = data['parse']
    assert result['split'] == ['devadattaH', 'grAmam', 'gacCati']
    assert result['status'] == 'OK'
    best = result['analysis'][0]
    relations = {g['node']['pada']: (g['sambandha'], g['predecessor'] and g['predecessor']['pada'])
                 for g in best['graph']}
    assert relations == {'devadattaH': ('kartA', 'gacCati'), 'grAmam': ('karma', 'gacCati'),
                         'gacCati': (None, None)}
    assert [g['node']['index'] for g in best['graph']] == [0, 1, 2]
    verb = best['graph'][2]['node']
    assert verb['root'] == 'gam' and 'law' in verb['tags']


def test_parse_costs_are_ascending_and_limited(gql):
    q = '{ parse(text: "%s", limit: 2, parseLimit: %d) { analysis { cost } } }'
    for parse_limit in (1, 4):
        for result in gql(q % (SENTENCE, parse_limit))['parse']:
            costs = [a['cost'] for a in result['analysis']]
            assert costs == sorted(costs) and 0 < len(costs) <= parse_limit


def test_parse_default_parse_limit_is_two(gql):
    data = gql('{ parse(text: "%s", limit: 1) { analysis { cost } } }' % SENTENCE)
    assert len(data['parse'][0]['analysis']) == 2


def test_parse_min_cost_only(gql):
    data = gql('{ parse(text: "%s", limit: 3, parseLimit: 50, minCostOnly: true) { analysis { cost } } }' % SENTENCE)
    for result in data['parse']:
        assert len({a['cost'] for a in result['analysis']}) == 1
    everything = gql('{ parse(text: "%s", limit: 3, parseLimit: 50) { analysis { cost } } }' % SENTENCE)
    assert any(len({a['cost'] for a in r['analysis']}) > 1 for r in everything['parse'])


def test_parse_is_repeatable(gql):
    """Ties in cost used to come back in a different order on each run."""
    q = '{ parse(text: "%s", limit: 3, parseLimit: 10) { %s } }' % (SENTENCE, PARSE_FIELDS)
    assert gql(q) == gql(q)


def test_parse_every_split_gets_analysed_on_its_own(gql):
    """Upstream piles each split's tags onto words shared with the next split."""
    together = gql('{ parse(text: "%s", strictIO: true, limit: 3, parseLimit: 100) { split analysis { cost } } }'
                   % SENTENCE)['parse']
    assert [r['split'] for r in together] == [
        ['devadattas', 'grAmam', 'gacCati'],
        ['deva', 'dattas', 'grAmam', 'gacCati'],
        ['devat', 'attar', 'grAmam', 'gacCati'],
    ]
    for result in together:
        alone = gql('query($t: String!) { parse(text: $t, %s, preSegmented: true, strictIO: true, parseLimit: 100)'
                    ' { split analysis { cost } } }' % SLP, t=' '.join(result['split']))['parse'][0]
        assert alone == result


def test_parse_presegmented(gql):
    data = gql('{ parse(text: "%s", schemeTo: IAST, preSegmented: true) { split status analysis { cost } } }' % SENTENCE)
    assert len(data['parse']) == 1
    assert data['parse'][0]['split'] == ['devadattaḥ', 'grāmam', 'gacchati']
    assert data['parse'][0]['status'] == 'OK'


def test_parse_strict_output_keeps_s(gql):
    q = ('{ parse(text: "devadattaH grAmam gacCati", %s, strictIO: %s, limit: 1) '
         '{ split analysis { graph { node { pada } } } } }')
    for strict, form in (('true', 'devadattas'), ('false', 'devadattaH')):
        (result,) = gql(q % (SLP, strict))['parse']
        assert result['split'][0] == form
        assert result['analysis'][0]['graph'][0]['node']['pada'] == form


def test_parse_split_without_analysis_says_so(gql):
    data = gql('{ parse(text: "శుక్లాంబరధరం విష్ణుం శశివర్ణం చతుర్భుజమ్", schemeFrom: TELUGU, limit: 2) '
               '{ split status analysis { cost } parseDots parseDotURLs } }')
    second = data['parse'][1]
    assert second['split'] == ['SuklAmbaraDaram', 'vizRum', 'SaSiva', 'fRam', 'caturBujam']
    assert second == {'split': second['split'], 'status': 'NO_PARSE', 'analysis': [],
                      'parseDots': [], 'parseDotURLs': []}


def test_parse_of_unknown_text_is_empty(gql):
    assert gql('{ parse(text: "xyzqq", %s) { split } }' % SLP)['parse'] == []


def test_parse_conll(gql):
    data = gql('{ parse(text: "%s", schemeTo: IAST, limit: 1, parseLimit: 1) { analysis { conll } } }' % SENTENCE)
    rows = [line.split('\t') for line in data['parse'][0]['analysis'][0]['conll'].split('\n')]
    assert [r[:4] + r[5:] for r in rows] == [
        ['1', 'devadattaḥ', '_', 'devadatta', '3', 'kartā'],
        ['2', 'grāmam', '_', 'grāma', '3', 'karma'],
        ['3', 'gacchati', '_', 'gam', '0', 'root'],
    ]
    assert rows[0][4] == 'ekavacanam|prathamāvibhaktiḥ|puṃlliṅgam'


def test_parse_dot_of_an_analysis(gql):
    data = gql('{ parse(text: "%s", limit: 1, parseLimit: 1) { analysis { dot dotURL } parseDots parseDotURLs } }' % SENTENCE)
    (result,) = data['parse']
    dot = result['analysis'][0]['dot']
    assert dot == ('digraph {\n'
                   '  n0_0 [label="devadattaH [devadatta, {ekavacanam, praTamAviBaktiH, puMlliNgam}]"];\n'
                   '  n1_1 [label="grAmam [grAma, {dvitIyAviBaktiH, ekavacanam, napuMsakaliNgam}]"];\n'
                   '  n2_2 [label="gacCati [gam, {ekavacanam, kartari, law, parasmEpadam, prATamikaH, praTamapuruzaH}]"];\n'
                   '  n2_2 -> n0_0 [label="kartA"];\n'
                   '  n2_2 -> n1_1 [label="karma"];\n'
                   '}\n')
    assert result['parseDots'] == [dot]
    url = result['analysis'][0]['dotURL']
    assert url.startswith('https://image-charts.com/chart?cht=gv%3Adot&chl=digraph+%7B')
    assert result['parseDotURLs'] == [url]


def test_parse_dot_follows_scheme_to_unless_told_otherwise(gql):
    data = gql('''{ parse(text: "%s", schemeTo: TELUGU, limit: 1, parseLimit: 1) {
        splitDot inIast: splitDot(scheme: IAST) splitDotURL
        analysis { dot inSlp1: dot(scheme: SLP1) }
        parseDots(scheme: SLP1)
    } }''' % SENTENCE)
    (result,) = data['parse']
    assert 'label="దేవదత్తః [దేవదత్త, ' in result['splitDot']
    assert 'label="కర్తా"' in result['analysis'][0]['dot']
    assert 'label="devadattaḥ [devadatta, ' in result['inIast']
    assert 'label="kartA"' in result['analysis'][0]['inSlp1']
    assert result['parseDots'] == [result['analysis'][0]['inSlp1']]
    assert result['splitDotURL'].startswith('https://image-charts.com/chart?')
    # DOT keywords and node ids stay ASCII whatever the scheme
    assert re.match(r'digraph \{\n  n0_0 \[label="', result['splitDot'])


def test_parse_split_dot_has_every_reading_and_relation(gql):
    data = gql('{ parse(text: "%s", limit: 1, parseLimit: 1) { splitDot analysis { dot } } }' % SENTENCE)
    (result,) = data['parse']
    split_nodes = re.findall(r'^  (n\d+_\d+) \[', result['splitDot'], re.M)
    parse_nodes = re.findall(r'^  (n\d+_\d+) \[', result['analysis'][0]['dot'], re.M)
    assert len(split_nodes) > len(parse_nodes) == 3
    assert {n.split('_')[0] for n in split_nodes} == {'n0', 'n1', 'n2'}
    assert result['splitDot'].count('->') > result['analysis'][0]['dot'].count('->')


@pytest.mark.parametrize('args, message', [
    ('limit: 0', 'limit must be at least 1'),
    ('parseLimit: 0', 'parseLimit must be at least 1'),
    ('preSegmented: true, limit: -1', 'limit must be at least 1'),
])
def test_parse_rejects_bad_limits(gql_error, args, message):
    assert gql_error('{ parse(text: "%s", %s) { split } }' % (SENTENCE, args)) == message


def test_parse_presegmented_unknown_word(gql_error):
    message = gql_error('{ parse(text: "rAmaH xyzzyq", %s, preSegmented: true) { split } }' % SLP)
    assert message == '"xyzzyq" is not a known word and cannot be split into known words'
