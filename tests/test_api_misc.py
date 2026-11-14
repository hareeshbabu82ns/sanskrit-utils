"""GraphQL: dhatus, pratyaharas, metre, transliteration, and the HTTP endpoint."""
import pytest

SLP = 'schemeFrom: SLP1'


# --- dhatus ---------------------------------------------------------------

def test_dhatu_entry(gql):
    data = gql('{ dhatus(dhatu: "gam", %s) { dhatu mulaDhatu artha gana karmakatva sakarmaka dvikarmaka ittva pada rupa } }' % SLP)
    assert data['dhatus'] == [{
        'dhatu': 'gam', 'mulaDhatu': 'gamlf', 'artha': 'gatO', 'gana': 'BvAdiH',
        'karmakatva': 'sakarmakaH', 'sakarmaka': True, 'dvikarmaka': False,
        'ittva': 'aniw', 'pada': 'parasmEpadI', 'rupa': 'gacCati',
    }]


def test_dhatu_with_several_entries_and_devanagari(gql):
    data = gql('{ dhatus(dhatu: "कृ", schemeTo: DEVANAGARI) { mulaDhatu gana pada } }')
    assert {'mulaDhatu': 'डुकृञ्', 'gana': 'तनादिः', 'pada': 'उभयपदी'} in data['dhatus']
    assert len(data['dhatus']) == 2


def test_dhatu_by_its_taught_form(gql):
    data = gql('{ dhatus(dhatu: "gamlf", %s) { dhatu } }' % SLP)
    assert data['dhatus'] == [{'dhatu': 'gam'}]


def test_dhatu_transitivity_flags(gql):
    q = 'query($d: String!) { dhatus(dhatu: $d, %s) { sakarmaka dvikarmaka } }' % SLP
    assert {'sakarmaka': False, 'dvikarmaka': False} in gql(q, d='BU')['dhatus']
    assert {'sakarmaka': True, 'dvikarmaka': True} in gql(q, d='nI')['dhatus']


def test_dhatu_unknown_and_empty(gql, gql_error):
    assert gql('{ dhatus(dhatu: "zzz", %s) { dhatu } }' % SLP)['dhatus'] == []
    assert gql_error('{ dhatus(dhatu: " ", %s) { dhatu } }' % SLP) == 'dhatu is empty'


# --- Maheshvara sutras and pratyaharas -------------------------------------

def test_maheshvara_sutras(gql):
    sutras = gql('{ maheshvaraSutras }')['maheshvaraSutras']
    assert len(sutras) == 14
    assert sutras[0] == 'अइउण्' and sutras[-1] == 'हल्'
    assert gql('{ maheshvaraSutras(schemeTo: SLP1) }')['maheshvaraSutras'][:4] == ['aiuR', 'fxk', 'eoN', 'EOc']


@pytest.mark.parametrize('name, varnas', [
    ('jaS', 'jbgqd'),
    ('ac', 'aiufxeoEO'),
    ('ik', 'iufx'),
    ('yaR', 'yvrl'),
    ('Jal', 'JBGQDjbgqdKPCWTcwtkpSzsh'),
])
def test_pratyahara(gql, name, varnas):
    data = gql('query($n: String!) { pratyahara(name: $n, %s) { name varnas } }' % SLP, n=name)
    assert data['pratyahara'] == {'name': name, 'varnas': list(varnas)}


def test_pratyahara_hal_has_every_consonant(gql):
    varnas = gql('{ pratyahara(name: "hal", %s) { varnas } }' % SLP)['pratyahara']['varnas']
    assert varnas[0] == varnas[-1] == 'h'  # h is taught twice
    assert set(varnas) == set('hyvrlYmNRnJBGQDjbgqdKPCWTcwtkpSzs')


def test_pratyahara_long_form_and_long_vowels(gql):
    q = '{ pratyahara(name: "aR", %s, %s) { varnas } }'
    assert gql(q % (SLP, 'longForm: false'))['pratyahara']['varnas'] == list('aiu')
    assert gql(q % (SLP, 'longForm: true'))['pratyahara']['varnas'] == list('aiufxeoEOhyvrl')
    assert gql(q % (SLP, 'longForm: false, withLongVowels: true'))['pratyahara']['varnas'] == list('aAiIuU')


def test_pratyahara_devanagari(gql):
    data = gql('{ pratyahara(name: "जश्", schemeTo: DEVANAGARI) { name varnas } }')
    assert data['pratyahara'] == {'name': 'जश्', 'varnas': ['ज्', 'ब्', 'ग्', 'ड्', 'द्']}


@pytest.mark.parametrize('name', ['zz', 'kaR', 'a', '', 'jaj'])
def test_pratyahara_rejects_what_is_not_one(gql_error, name):
    message = gql_error('query($n: String!) { pratyahara(name: $n, %s) { name } }' % SLP, n=name)
    assert message == '"%s" is not a pratyahara' % name


# --- meter ----------------------------------------------------------------

VERSE = 'शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।\nप्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥'


def test_meter_scans_each_line(gql):
    data = gql('query($t: String!) { meter(text: $t, schemeTo: IAST) { text syllables pattern } }', t=VERSE)
    assert data['meter'] == [
        {'text': 'śuklāmbaradharaṃ viṣṇuṃ śaśivarṇaṃ caturbhujam', 'syllables': 16, 'pattern': 'GGLLLGGGLLGGLGLL'},
        {'text': 'prasannavadanaṃ dhyāyet sarvavighnopaśāntaye', 'syllables': 16, 'pattern': 'LGLLLGGGGLGGLGLG'},
    ]


@pytest.mark.parametrize('text, pattern', [
    ('rAmaH', 'GG'),        # long vowel; vowel before visarga
    ('deva', 'GL'),
    ('aMSa', 'GL'),         # vowel before anusvara
    ('satya', 'GL'),        # short vowel before a conjunct
    ('tat tvam', 'GL'),     # the conjunct may span two words
    ('a', 'L'),
])
def test_meter_weights(gql, text, pattern):
    data = gql('query($t: String!) { meter(text: $t, %s) { syllables pattern } }' % SLP, t=text)
    assert data['meter'] == [{'syllables': len(pattern), 'pattern': pattern}]


def test_meter_needs_syllables(gql_error):
    assert gql_error('{ meter(text: "123 |", %s) { pattern } }' % SLP) == 'text has no Sanskrit syllables in it'


# --- transliterate, version ------------------------------------------------

def test_transliterate(gql):
    assert gql('{ transliterate(text: "harIS", schemeFrom: SLP1, schemeTo: DEVANAGARI) }')['transliterate'] == 'हरीश्'
    assert gql('{ transliterate(text: "हरि") }')['transliterate'] == 'hari'
    assert gql('{ transliterate(text: "హరి", schemeFrom: TELUGU, schemeTo: IAST) }')['transliterate'] == 'hari'


@pytest.mark.parametrize('schemes', ['schemeFrom: ENGLISH', 'schemeTo: ENGLISH'])
def test_transliterate_rejects_english(gql_error, schemes):
    message = gql_error('{ transliterate(text: "hari", %s) }' % schemes)
    assert message == 'ENGLISH is not a script that text can be converted to or from'


def test_version(gql):
    assert gql('{ version }') == {'version': 'test'}


# --- schema ----------------------------------------------------------------

def test_every_query_argument_default_is_declared_in_the_schema(schema):
    """Defaults live in the SDL so that clients and the explorer can see them."""
    fields = schema.query_type.fields
    for name in ('splits', 'splitPairs', 'joins', 'tags', 'presegmented', 'parse',
                 'dhatus', 'pratyahara', 'meter', 'transliterate'):
        args = fields[name].args
        assert args['schemeFrom'].default_value is not None, name
        assert args['schemeTo'].default_value is not None, name


def test_parse_types_are_non_null_where_the_resolvers_guarantee_it(schema):
    parse = schema.type_map['Parse'].fields
    assert str(parse['analysis'].type) == '[ParseItem!]!'
    assert str(parse['split'].type) == '[String!]!'
    assert str(schema.type_map['ParseGraph'].fields['node'].type) == 'ParseTag!'


# --- HTTP ------------------------------------------------------------------

def test_http_get_serves_the_explorer(client):
    response = client.get('/graphql')
    assert response.status_code == 200
    assert b'<html' in response.data.lower()


def test_http_post_runs_a_query(client):
    response = client.post('/graphql', json={
        'query': 'query($t: String!) { tags(text: $t, schemeFrom: SLP1) { word } version }',
        'variables': {'t': 'rAmaH'}})
    assert response.status_code == 200
    body = response.get_json()
    assert body['data']['version'] == 'v1.0'
    assert {'word': 'rAma'} in body['data']['tags']


def test_http_post_reports_resolver_errors(client):
    response = client.post('/graphql', json={'query': '{ joins(words: ["eka"]) }'})
    body = response.get_json()
    assert body['errors'][0]['message'] == 'joins needs at least two words'
    assert body['errors'][0]['path'] == ['joins']


def test_http_post_rejects_an_invalid_query(client):
    response = client.post('/graphql', json={'query': '{ noSuchField }'})
    assert response.status_code == 400
    assert 'noSuchField' in response.get_json()['errors'][0]['message']
