from sanskrit_parser import Parser

from sanskrit_parser.base.sanskrit_base import SCHEMES
from sanskrit_parser.base.sanskrit_base import SanskritObject, SanskritNormalizedString, SLP1, TELUGU, SCHEMES as PARSER_SCHEMES
from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer

SANS_TO_PARSER_SCHEMES_MAP = {v: k for k, v in PARSER_SCHEMES.items()}
# print(SCHEMES)
# print(SANS_TO_PARSER_SCHEMES_MAP)

analyzer = LexicalSandhiAnalyzer()

# """Splits with analyzer"""
# text = 'कालिदासस्य जीवनवृत्तिविषये अनेकाः लोकविश्रुतयः अनेके वादाः च सन्ति'
# vobj = SanskritObject(text, strict_io=False,
#                       replace_ending_visarga=None)
# g = analyzer.getSandhiSplits(vobj)
# if g:
#     splits = g.find_all_paths(10)
#     [[print(type(ss)) for ss in s] for s in splits]
#     jsplits = [[ss.devanagari(strict_io=False)
#                 for ss in s] for s in splits]
# else:
#     jsplits = []
# print(jsplits)


# """Splits with Parser"""
# parser = Parser(output_encoding='Telugu')
# parser.output_encoding = 'devanagari'
# # parser = Parser(output_encoding='Devanagari')

# text = 'कालिदासस्य जीवनवृत्तिविषये अनेकाः लोकविश्रुतयः अनेके वादाः च सन्ति'
# # text = 'तस्मात्समस्तक्षत्रवर्गगर्वपाटनवरिष्ठधारापरश्वधभरणभीषणवेषभार्गवभङ्गादपरिच्छिन्नतरशौर्यशालिनि'
# splits = parser.split(text, limit=10)
# [[print(type(ss)) for ss in s.split] for s in splits]
# for split in splits:
#     print(type(split))
#     print(f'{split}')

# """Tags with Parser"""
# sentence = 'देवदत्तः ग्रामं गच्छति'

# split = parser.split(sentence, pre_segmented=True)[0]
# print(f'{split}')

# parses = list(split.parse(limit=2))
# for i, parse in enumerate(parses):
#     print(f'Parse {i}')
#     print(f'{parse}')

# print(parses[0].to_dot())


"""Sandhi Joins"""
first_in = SanskritNormalizedString(
    'jIvan', encoding=SLP1, strict_io=True)
second_in = SanskritNormalizedString(
    'avftti', encoding=SLP1, strict_io=True)
joins = analyzer.sandhi.join(first_in, second_in)

sjoins = [SanskritNormalizedString(join, encoding=SLP1, strict_io=True).transcoded(
    TELUGU, True) for join in list(joins)]

print(sjoins)