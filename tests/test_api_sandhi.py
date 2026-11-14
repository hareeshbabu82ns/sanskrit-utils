"""GraphQL: splits, splitPairs, joins, presegmented."""
import pytest

SLP = 'schemeFrom: SLP1'


def test_splits_returns_best_split_first(gql):
    data = gql('{ splits(text: "astyuttarasyAMdiSidevatAtmA", %s, limit: 3) }' % SLP)
    assert data['splits'][0] == ['asti', 'uttarasyAm', 'diSi', 'devatAtmA']
    assert len(data['splits']) == 3
    assert len({tuple(s) for s in data['splits']}) == 3


def test_splits_defaults_devanagari_in_slp1_out(gql):
    assert gql('{ splits(text: "तस्मिन्निति", limit: 1) }')['splits'] == [['tasmin', 'iti']]


def test_splits_output_scheme(gql):
    data = gql('{ splits(text: "तस्मिन्निति", schemeTo: TELUGU, limit: 1) }')
    assert data['splits'] == [['తస్మిన్', 'ఇతి']]


def test_splits_limit_is_respected(gql):
    assert len(gql('{ splits(text: "astyuttarasyAMdiSidevatAtmA", %s, limit: 1) }' % SLP)['splits']) == 1


def test_splits_of_unknown_text_is_empty(gql):
    assert gql('{ splits(text: "xyzqq", %s) }' % SLP)['splits'] == []


@pytest.mark.parametrize('strict, last', [(False, 'gacCati'), (True, 'gacCati')])
def test_splits_visarga_output_follows_strict_io(gql, strict, last):
    data = gql('query($s: Boolean) { splits(text: "rAmaH gacCati", %s, strictIO: $s, limit: 1) }' % SLP, s=strict)
    # non-strict shows the visarga the user typed; strict keeps the parser's s/r
    assert data['splits'] == [['rAmas' if strict else 'rAmaH', last]]


def test_splits_reads_anusvara_before_a_stop_as_the_class_nasal(gql):
    """`శుక్లాంబర` is spelt with anusvara; the lexicon has `SuklAmbara`."""
    for strict in ('true', 'false'):
        data = gql('{ splits(text: "శుక్లాంబరధరం విష్ణుం శశివర్ణం చతుర్భుజమ్", schemeFrom: TELUGU,'
                   ' strictIO: %s, limit: 1) }' % strict)
        assert data['splits'] == [['SuklAmbaraDaram', 'vizRum', 'SaSi', 'varRam', 'caturBujam']], strict


def test_splits_strict_leaves_a_final_anusvara_alone(gql):
    q = '{ splits(text: "rAmaH vanaM", %s, strictIO: %s, limit: 1) }'
    assert gql(q % (SLP, 'false'))['splits'] == [['rAmaH', 'vanam']]
    assert gql(q % (SLP, 'true'))['splits'] == []  # `vanaM` is not a word; `vanam` is


def test_splits_keeps_anusvara_before_a_semivowel(gql):
    """Upstream turns saMyoga into say~yoga, which no lexicon has."""
    assert gql('{ splits(text: "saMyogaH Bavati", %s, limit: 1) }' % SLP)['splits'] == [['saMyogaH', 'Bavati']]


def test_splits_ignores_punctuation_digits_and_dandas(gql):
    data = gql('{ splits(text: "रामः, गच्छति ॥ १ ॥", limit: 1) }')
    assert data['splits'] == [['rAmaH', 'gacCati']]


@pytest.mark.parametrize('args, message', [
    ('text: "...", schemeFrom: SLP1', 'text has no Sanskrit letters in it'),
    ('text: "rAmaH", schemeFrom: SLP1, limit: 0', 'limit must be at least 1'),
    ('text: "rAmaH", schemeFrom: ENGLISH', 'ENGLISH is not a script that text can be converted to or from'),
    ('text: "rAmaH", schemeTo: ENGLISH, schemeFrom: SLP1', 'ENGLISH is not a script that text can be converted to or from'),
])
def test_splits_rejects_bad_input(gql_error, args, message):
    assert gql_error('{ splits(%s) }' % args) == message


def test_splits_rejects_overlong_text(gql_error, service):
    text = 'rAmaH ' * (service.MAX_TEXT_LENGTH // 6 + 1)
    assert 'too long' in gql_error('query($t: String!) { splits(text: $t, %s) }' % SLP, t=text)


def test_null_scheme_falls_back_to_the_default(gql):
    data = gql('{ splits(text: "तस्मिन्निति", schemeFrom: null, schemeTo: null, strictIO: null, limit: 1) }')
    assert data['splits'] == [['tasmin', 'iti']]


# --- splitPairs -----------------------------------------------------------

def test_split_pairs_valid_only(gql):
    data = gql('{ splitPairs(text: "tasminniti", %s, validOnly: true) { left right valid } }' % SLP)
    assert data['splitPairs'] == [{'left': 'tasmin', 'right': 'iti', 'valid': True}]


def test_split_pairs_lists_valid_pairs_first(gql):
    pairs = gql('{ splitPairs(text: "tasminniti", %s) { left right valid } }' % SLP)['splitPairs']
    assert pairs[0] == {'left': 'tasmin', 'right': 'iti', 'valid': True}
    assert any(not p['valid'] for p in pairs)
    flags = [p['valid'] for p in pairs]
    assert flags == sorted(flags, reverse=True)
    assert all(p['left'] and p['right'] for p in pairs)


def test_split_pairs_at_a_position(gql):
    pairs = gql('{ splitPairs(text: "tasminniti", %s, position: 5) { left right } }' % SLP)['splitPairs']
    assert {'left': 'tasmin', 'right': 'niti'} in pairs
    assert {p['right'] for p in pairs} == {'niti'}


def test_split_pairs_shows_final_s_and_r_as_visarga_unless_strict(gql):
    q = '{ splitPairs(text: "taeva", %s, position: 1, strictIO: %s) { left right } }'
    loose = gql(q % (SLP, 'false'))['splitPairs']
    strict = gql(q % (SLP, 'true'))['splitPairs']
    assert {'left': 'taH', 'right': 'eva'} in loose
    assert len(loose) == len({(p['left'], p['right']) for p in loose})
    assert {p['left'] for p in strict} >= {'tas', 'tar', 'ta'}


def test_split_pairs_output_scheme(gql):
    data = gql('{ splitPairs(text: "तस्मिन्निति", schemeTo: IAST, validOnly: true) { left right } }')
    assert data['splitPairs'] == [{'left': 'tasmin', 'right': 'iti'}]


@pytest.mark.parametrize('args, message', [
    ('text: "tasminniti", position: 10', 'position must be between 0 and 9'),
    ('text: "tasminniti", position: -1', 'position must be between 0 and 9'),
    ('text: "tasmin iti"', 'splitPairs works on a single word; use splits for a sentence'),
])
def test_split_pairs_rejects_bad_input(gql_error, args, message):
    assert gql_error('{ splitPairs(%s, %s) { left } }' % (args, SLP)) == message


# --- joins ----------------------------------------------------------------

def test_joins_two_words(gql):
    assert gql('{ joins(words: ["tasmin", "iti"], %s) }' % SLP)['joins'] == ['tasminiti', 'tasminniti']


def test_joins_transliterates_both_ways(gql):
    data = gql('{ joins(words: ["కాలి", "దాసస్య"], schemeFrom: TELUGU, schemeTo: TELUGU) }')
    assert data['joins'] == ['కాలిదాసస్య']


def test_joins_lists_fully_joined_forms_first(gql):
    assert gql('{ joins(words: ["te", "eva"], %s) }' % SLP)['joins'] == ['taeva', 'tayeva', 'teeva', 'ta eva']


def test_joins_reads_a_final_visarga_as_s(gql):
    joins = gql('{ joins(words: ["rAmaH", "gacCati"], %s) }' % SLP)['joins']
    assert 'rAmo gacCati' in joins


def test_joins_more_than_two_words_keeps_every_combination(gql):
    """The old resolver only carried the first candidate into the next join."""
    joins = gql('{ joins(words: ["asti", "uttarasyAm", "diSi", "devatA", "AtmA"], %s) }' % SLP)['joins']
    assert 'astyuttarasyAMdiSidevatAtmA' in joins
    assert len(joins) == len(set(joins)) > 4


def test_joins_three_words(gql):
    joins = gql('{ joins(words: ["tasmin", "iti", "eva"], %s) }' % SLP)['joins']
    assert joins == ['tasminitieva', 'tasminityeva', 'tasminnitieva', 'tasminnityeva']


def test_joins_needs_two_words(gql_error):
    assert gql_error('{ joins(words: ["eka"], %s) }' % SLP) == 'joins needs at least two words'
    assert gql_error('{ joins(words: [], %s) }' % SLP) == 'joins needs at least two words'


def test_splits_undo_joins(gql):
    words = ['asti', 'uttarasyAm', 'diSi']
    joined = gql('query($w: [String!]!) { joins(words: $w, %s) }' % SLP, w=words)['joins']
    assert 'astyuttarasyAMdiSi' in joined
    assert gql('{ splits(text: "astyuttarasyAMdiSi", %s, limit: 1) }' % SLP)['splits'] == [words]


# --- presegmented ---------------------------------------------------------

def test_presegmented_normalises_each_word(gql):
    data = gql('{ presegmented(text: "దేవదత్తః గ్రామం గచ్ఛతి", schemeFrom: TELUGU, schemeTo: TELUGU) }')
    assert data['presegmented'] == ['దేవదత్తః', 'గ్రామమ్', 'గచ్ఛతి']


def test_presegmented_strict_output_tells_s_from_r(gql):
    data = gql('{ presegmented(text: "rAmaH punaH gacCati", %s) }' % SLP)
    assert data['presegmented'] == ['rAmaH', 'punaH', 'gacCati']
    # strict input has to spell the endings out, and gets them back
    data = gql('{ presegmented(text: "rAmas punar gacCati", %s, strictIO: true) }' % SLP)
    assert data['presegmented'] == ['rAmas', 'punar', 'gacCati']


def test_presegmented_splits_a_word_it_does_not_know_whole(gql):
    data = gql('{ presegmented(text: "rAmaH vanaMgacCati", %s) }' % SLP)
    assert data['presegmented'] == ['rAmaH', 'vanam', 'gacCati']


def test_presegmented_accepts_the_deprecated_limit(gql):
    assert gql('{ presegmented(text: "rAmaH", %s, limit: 3) }' % SLP)['presegmented'] == ['rAmaH']


def test_presegmented_names_the_word_it_cannot_place(gql_error):
    """Upstream dies with a TypeError here."""
    message = gql_error('{ presegmented(text: "devadattaH xyzzyq gacCati", %s) }' % SLP)
    assert message == '"xyzzyq" is not a known word and cannot be split into known words'


def test_presegmented_strict_hints_at_the_spelling(gql_error):
    message = gql_error('{ presegmented(text: "grAmaM", %s, strictIO: true) }' % SLP)
    assert message.startswith('"grAmaM" is not a known word')
    assert 'strictIO is on' in message
