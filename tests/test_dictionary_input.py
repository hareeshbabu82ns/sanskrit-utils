"""Dictionary mutations: shaping the input document (no MongoDB involved)."""
from sanskrit_utils.schema.Sanscript import (Dictionaries, SanscriptScheme,
                                             prepare_dict_item_from_input)


def test_new_item_gets_every_field():
    doc = prepare_dict_item_from_input({
        'word': 'hari', 'description': 'a name of Vishnu', 'origin': Dictionaries.MW,
        'wordTranslations': [{'language': SanscriptScheme.SLP1, 'value': 'hari'},
                             {'language': SanscriptScheme.DEVANAGARI, 'value': 'हरि'}],
    })
    assert doc == {
        'wordIndex': 0, 'wordOriginal': 'hari', 'descOriginal': 'a name of Vishnu',
        'word': {'slp1': 'hari', 'devanagari': 'हरि'}, 'desc': {}, 'origin': 'mw',
    }


def test_new_item_defaults():
    doc = prepare_dict_item_from_input({})
    assert doc == {'wordIndex': 0, 'wordOriginal': '', 'descOriginal': '',
                   'word': {}, 'desc': {}, 'origin': 'others'}


def test_original_falls_back_to_the_first_translation():
    doc = prepare_dict_item_from_input({
        'wordTranslations': [{'language': SanscriptScheme.SLP1, 'value': 'hari'}]})
    assert doc['wordOriginal'] == 'hari' and doc['word'] == {'slp1': 'hari'}


def test_update_only_sets_what_was_given():
    assert prepare_dict_item_from_input({'description': 'new'}, update=True) == {'descOriginal': 'new'}
    assert prepare_dict_item_from_input({}, update=True) == {}
    doc = prepare_dict_item_from_input({
        'wordIndex': 7, 'origin': Dictionaries.VCP,
        'descriptionTranslations': [{'language': SanscriptScheme.ENGLISH, 'value': 'text'}],
    }, update=True)
    assert doc == {'wordIndex': 7, 'origin': 'vcp', 'desc': {'english': 'text'}}
