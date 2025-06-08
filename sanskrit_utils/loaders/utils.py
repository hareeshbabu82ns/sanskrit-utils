import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


def generate_phonetic_string(word_array, description_array, max_length=1000):
    """
    Generate a condensed phonetic string from word and description arrays
    for full text search optimization. Filters out duplicates, common articles,
    grammatical strings, and special characters.

    Args:
        word_array: List of dicts with 'lang' and 'value' keys
        description_array: List of dicts with 'lang' and 'value' keys

    Returns:
        str: Space-separated phonetic string combining all transliterations
    """

    all_words = []

    # Extract word values from all languages
    for word_item in word_array:
        if word_item.get('value'):
            word_value = word_item['value'].strip()
            if word_value:  # Only process non-empty values
                # Get transliterated versions for non-English words
                transliterated_words = get_transliterated_words(word_item)
                # print(
                #     f"Transliterated words for '{word_value}': {transliterated_words}")
                for trans_word in transliterated_words:
                    words = extract_meaningful_words(
                        trans_word, max_length=max_length)
                    all_words.extend(words)

    # Extract description values with more aggressive filtering
    for desc_item in description_array:
        if desc_item.get('value'):
            desc_value = desc_item['value'].strip()
            if desc_value:  # Only process non-empty values
                # Get transliterated versions for non-English descriptions
                transliterated_words = get_transliterated_words(desc_item)
                for trans_word in transliterated_words:
                    words = extract_meaningful_words(
                        trans_word, max_length=max_length)
                    all_words.extend(words)

    # Remove duplicates while preserving order and applying additional filters
    seen = set()
    unique_words = []

    for word in all_words:
        # Convert to lowercase for deduplication
        word_lower = word.lower()

        # Skip if already seen
        if word_lower in seen:
            continue

        # Skip very short words
        if len(word_lower) < 2:
            continue

        # Skip words that are mostly punctuation or special characters
        # a-zA-Z0-9: Basic Latin alphanumeric
        # \u0100-\u017F: Latin Extended-A (ā, ī, ū, ṛ, ṝ, ḷ, ḹ, etc.)
        # \u1E00-\u1EFF: Latin Extended Additional (ṭ, ḍ, ṇ, ś, ṣ, ṃ, ḥ, etc.)
        # \u0900-\u097F: Devanagari Unicode range (for Sanskrit)
        # \u0C00-\u0C7F: Telugu Unicode range
        if len(re.sub(r'[a-zA-Z0-9\u0100-\u017F\u1E00-\u1EFF\u0900-\u097F\u0C00-\u0C7F]', '', word)) > len(word) * 0.5:
            # print(f"Skipping word due to excessive special characters: {word}")
            continue

        seen.add(word_lower)
        unique_words.append(word)

    # Join words and normalize final whitespace
    phonetic_string = ' '.join(unique_words)

    # Final cleanup: remove any remaining multiple spaces
    phonetic_string = ' '.join(phonetic_string.split())

    # Limit final string length to prevent excessive bloat
    # if len(phonetic_string) > max_length:
    #     phonetic_string = phonetic_string[:max_length].rsplit(' ', 1)[0]

    return phonetic_string


def get_transliterated_words(item):
    """
    Get transliterated versions of a word/description item.
    For non-English languages, returns ITRANS and SLP1 transliterations.
    For English, returns the original value.

    Args:
        item: Dict with 'lang' and 'value' keys

    Returns:
        List of transliterated strings
    """
    if not item.get('value'):
        return []

    lang = item.get('lang', '').upper()
    value = item['value'].strip()

    if not value:
        return []

    # For English, return original value
    if lang == 'ENG':
        return [value]

    # Language mapping for transliteration
    lang_map = {
        'SAN': sanscript.DEVANAGARI,
        'TEL': sanscript.TELUGU,
        'IAST': sanscript.IAST,
        'ITRANS': sanscript.ITRANS,
        'SLP1': sanscript.SLP1
    }

    # If language is not in our map, treat as original
    if lang not in lang_map:
        return [value]

    transliterated_words = []

    try:
        # Add ITRANS transliteration if not already ITRANS
        if lang != 'ITRANS':
            itrans_value = transliterate(
                value, lang_map[lang], sanscript.ITRANS)
            if itrans_value and itrans_value != value:
                transliterated_words.append(itrans_value)

        # Add SLP1 transliteration if not already SLP1
        elif lang != 'SLP1':
            slp1_value = transliterate(value, lang_map[lang], sanscript.SLP1)
            if slp1_value and slp1_value != value:
                transliterated_words.append(slp1_value)

        else:
            # If already SLP1 or ITRANS, just return original value
            transliterated_words.append(value)

    except Exception as e:
        # If transliteration fails, just return original value
        print(f"Transliteration error for '{value}' from {lang}: {e}")
        return [value]

    return transliterated_words


# Common articles, prepositions, and grammatical words to filter out
STOP_WORDS = {
    # English
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall',
    'this', 'that', 'these', 'those', 'he', 'she', 'it', 'they', 'we',
    'you', 'i', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
    'her', 'its', 'our', 'their', 'also', 'only', 'just', 'very', 'more',
    'most', 'such', 'some', 'any', 'each', 'every', 'all', 'both', 'either',
    'neither', 'same', 'different', 'other', 'another', 'one', 'two', 'first',
    'last', 'next', 'previous', 'many', 'much', 'few', 'little', 'less',
    'least', 'than', 'then', 'now', 'here', 'there', 'where', 'when', 'why',
    'how', 'what', 'which', 'who', 'whom', 'whose', 'if', 'unless', 'until',
    'while', 'during', 'before', 'after', 'above', 'below', 'up', 'down',
    'out', 'over', 'under', 'again', 'further', 'once', 'see', 'used',
    'name', 'epithet', 'term', 'word', 'meaning', 'called', 'known',

    # Punctuation and formatting words
    'said', 'says', 'called', 'named', 'known', 'also', 'see', 'cf', 'etc',
    'viz', 'lit', 'literally', 'figuratively', 'metaphorically', 'esp',
    'especially', 'particularly', 'generally', 'usually', 'commonly',
    'often', 'sometimes', 'always', 'never', 'rarely', 'frequently'

    # Telugu grammatical terms (common in dictionaries)
    'అను', 'అందు', 'అందువల్ల', 'అంటే', 'అయితే', 'ఇది', 'కాదు', 'ఇలా',
    'మాత్రమే', 'కాని', 'అయిన', 'అయినప్పటికీ',

    # Sanskrit grammatical terms (common in dictionaries)
    'च', 'वा', 'तु', 'हि', 'एव', 'अपि', 'तथा', 'यथा', 'इति', 'किन्तु',
    'परन्तु', 'अथवा', 'यदि', 'चेत्', 'तर्हि', 'तदा', 'सः', 'सा', 'तत्',
    'ते', 'ताः', 'तानि', 'एषः', 'एषा', 'एतत्', 'एते', 'एताः', 'एतानि',

    # Common words that appear in transliterations
    'చ', 'వా', 'తు', 'హి', 'ఏవ', 'అపి', 'తథా', 'యథా', 'ఇతి', 'కిన్తు',
    'పరన్తు', 'అథవా', 'యది', 'చేత్', 'తర్హి', 'తదా', 'సః', 'సా', 'తత్',
    'తే', 'తాః', 'తాని', 'ఏషః', 'ఏషా', 'ఏతత్', 'ఏతే', 'ఏతాః', 'ఏతాని',
    'vā', 'tu', 'tathā', 'yathā',
    'athavā', 'tadā', 'saḥ', 'sā',
    'tāḥ', 'tāni', 'eṣaḥ', 'eṣā', 'etāḥ', 'etāni',
    'ca', 'vA', 'tu', 'eva', 'taTA', 'yaTA',
    'aTavA', 'cet', 'tadA', 'saH', 'sA',
    'te', 'tAH', 'tAni', 'ezaH', 'ezA', 'etat', 'ete', 'etAH', 'etAni',
    'cha', 'vA', 'tu', 'hi', 'Eva', 'api', 'tathA', 'yathA', 'iti', 'kintu',
    'parantu', 'athavA', 'yadi', 'chEt', 'tarhi', 'tadA', 'saH', 'sA', 'tat',
    'tE', 'tAH', 'tAni', 'EShaH', 'EShA', 'Etat', 'EtE', 'EtAH', 'EtAni',

}

# Pattern to match special characters and HTML tags
SPECIAL_CHARS_PATTERN = re.compile(
    r'[<>{}[\]().,;:!?"\'\-_=+*/\\|`~@#$%^&“”‘’]+')

# Pattern to match numbers and single characters
NUMBER_PATTERN = re.compile(r'^\d+$')


def clean_text(text):
    """Clean and normalize text for phonetic indexing"""
    if not text:
        return ''

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove special characters but keep spaces and basic punctuation
    text = SPECIAL_CHARS_PATTERN.sub(' ', text)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text.lower()


def extract_meaningful_words(text, max_length=1000):
    """Extract meaningful words from text, filtering out stop words"""
    if not text:
        return []

    # Limit text length to avoid bloat
    if len(text) > max_length:
        text = text[:max_length]

    cleaned_text = clean_text(text)
    words = cleaned_text.split()

    meaningful_words = []
    for word in words:
        # Skip if word is too short (less than 2 characters)
        if len(word) < 2:
            continue

        # Skip if word is a number
        if NUMBER_PATTERN.match(word):
            continue

        # Skip if word is in stop words list
        if word in STOP_WORDS:
            continue

        # Skip if word is too long (likely corrupted or not meaningful)
        if len(word) > 50:
            continue

        meaningful_words.append(word)

    return meaningful_words
