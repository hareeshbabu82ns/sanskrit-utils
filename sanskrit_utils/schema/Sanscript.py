import enum
from ariadne import EnumType
from sanskrit_utils.schema import query
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

# sanscriptSchemesEnum = EnumType("SanscriptScheme",{
#   "DEVANAGARI" : sanscript.DEVANAGARI,
#   "IAST" : sanscript.IAST,
#   "ITRANS" : sanscript.ITRANS,
#   "SLP1" : sanscript.SLP1,
#   "TELUGU" : sanscript.TELUGU,
#   "TAMIL" : sanscript.TAMIL,
#   "KANNADA" : sanscript.KANNADA
# })

class SanscriptScheme(enum.Enum):
  DEVANAGARI = sanscript.DEVANAGARI
  IAST = sanscript.IAST
  ITRANS = sanscript.ITRANS
  SLP1 = sanscript.SLP1
  TELUGU = sanscript.TELUGU
  TAMIL = sanscript.TAMIL
  KANNADA = sanscript.KANNADA

sanscriptSchemesEnum = EnumType("SanscriptScheme", SanscriptScheme) 

# Map resolvers to fields in Query type using decorator syntax...
@query.field("transliterate")
def resolve_hello(_, info,text,schemeFrom=SanscriptScheme.DEVANAGARI,schemeTo=SanscriptScheme.SLP1):
    # return f'{text},{schemeFrom},{schemeTo}'
    return transliterate(text, schemeFrom.value, schemeTo.value)