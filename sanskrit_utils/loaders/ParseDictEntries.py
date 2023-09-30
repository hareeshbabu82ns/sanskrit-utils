
import os
from pymongo import MongoClient, IndexModel, ASCENDING, TEXT

# MONGO_DB_PASSWORD = pwd  \
#     MONGO_DB_HOST = 192.168.0.10  \
#     MONGO_DB_PORT = 3333  \
#     python sanskrit_utils/loaders/ParseDictEntries.py


mdbHost = os.environ.get('MONGO_DB_HOST', 'localhost')
mdbPort = os.environ.get('MONGO_DB_PORT', '21017')
mdbDB = os.environ.get('MONGO_DB_DB', 'sansutils')
mdbUser = os.environ.get('MONGO_DB_USER', 'sansutils')
mdbPassword = os.environ.get('MONGO_DB_PASSWORD', '')

# mongodb://sansutils:pwd@192.168.0.10:3333/sansutils
mdbUrl = f'mongodb://{mdbUser}:{mdbPassword}@{mdbHost}:{mdbPort}/{mdbDB}'
# mdbUrl = 'mongodb://{mdbUser}:{mdbPassword}'
print('MongoDB connecting to:', mdbUrl)

myclient = MongoClient(mdbUrl)

mydb = myclient[mdbDB]

dictEntriesCollection = mydb["dictEntries"]
dictPhoneticsEntriesCollection = mydb["dictPhonetics"]

slp1_replacements = {'A': 'aa', 'I': 'ii', 'U': 'uu', 'E': 'ee',
                     'O': 'oo', 'f': 'ru', 'F': 'ruu', 'x': 'lru', 'X': 'lruu',
                     'w': 't', 'W': 't', 't': 'th', 'T': 'th',
                     'q': 'd', 'Q': 'd', 'd': 'd', 'D': 'dh',
                     'N': 'gn', 'Y': 'ny', 'R': 'n', 'z': 'sh'}

# Example usage:
# input_string = "Hello, world!"
# replacements = {'o': '0', 'l': '1'}
# result = replace_chars(input_string, replacements)


def replace_chars(input_string, replacements):
    """
    Replace characters in the input_string based on the replacements dictionary.

    Args:
        input_string (str): The string to be processed.
        replacements (dict): A dictionary where keys are characters to be replaced
                            and values are the replacement characters.

    Returns:
        str: The input_string with characters replaced.
    """
    for old_char, new_char in replacements.items():
        input_string = input_string.replace(old_char, new_char)
    return input_string

# Example usage:
# input_string = "Hello, world!"
# replacements = {'o': '0', 'l': '1'}
# result = replace_chars_and_return_array(input_string, replacements)


def replace_chars_and_return_array(input_string, replacements):
    """
    Replace characters in the input_string based on the replacements dictionary
    and return an array of tuples with the original word and the replaced word.

    Args:
        input_string (str): The string to be processed.
        replacements (dict): A dictionary where keys are characters to be replaced
                            and values are the replacement characters.

    Returns:
        list of tuple: Each tuple contains the original word and the replaced word.
    """
    words = input_string.split()  # Split the input string into words
    result = set()

    for word in words:
        replaced_word = word  # Initialize replaced_word with the original word

        # Replace characters in the word based on the replacements dictionary
        for old_char, new_char in replacements.items():
            replaced_word = replaced_word.replace(old_char, new_char)

        # Append a tuple containing the original word and the replaced word to the result list
        result.add((word, replaced_word))

    return list(result)


def push_to_mongodb(words):

    for word in words:

        try:
            record = {"_id": word[1].lower(),
                      "word": word[0]}
            dictPhoneticsEntriesCollection.insert_one(record)

            record = {"_id": word[0],
                      "word": word[0]}
            dictPhoneticsEntriesCollection.insert_one(record)
        except:
            continue
        # print(record)


def parse_dict_entries():
    limit = 1000
    skip = 0
    words = []
    words_count = 0
    has_rows = True

    while has_rows:
        res = dictEntriesCollection.find(None).skip(skip).limit(limit)
        print('processing from:', skip, end='\n')
        (has_rows, words) = parse_dict_entry_block(res)
        skip += limit
        words_count += words.__len__()

    # res = dictEntriesCollection.find(None).skip(skip).limit(limit)
    # print('processing from:', skip, end='\n')
    # words = parse_dict_entry_block(res)
    # words_count += words.__len__()
    # while words.__len__() > 0:
    #     skip += limit
    #     res = dictEntriesCollection.find(None).skip(skip).limit(limit)
    #     print('processing from:', skip, end='\n')
    #     words = parse_dict_entry_block(res)
    #     words_count += words.__len__()

    print('processed words:', words_count)


def parse_dict_entry_block(res):
    final_words = []
    has_rows = False

    for row in res:
        has_rows = True
        input_word_string = ''
        input_desc_string = ''

        try:
            input_word_string = row['word']['slp1']
        except:
            input_word_string = ''

        # try:
        #     input_desc_string = row['desc']['slp1']
        # except:
        #     input_desc_string = ''

        input_string = input_word_string + ' ' + input_desc_string
        result = replace_chars_and_return_array(
            input_string.strip().replace(',', ' ').replace('.', ' '), slp1_replacements)
        final_words.extend(result)
        # print(result, end='\n\n')

    # print(final_words, end='\n\n')
    print('processed words:', final_words.__len__(), end='\n\n')
    push_to_mongodb(final_words)
    return (has_rows, final_words)


if __name__ == '__main__':
    parse_dict_entries()
