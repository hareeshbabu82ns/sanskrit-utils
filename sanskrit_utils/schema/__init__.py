import os

from ariadne import load_schema_from_path, make_executable_schema

# Order matters: Query/Mutation create the root ObjectTypes that the modules
# below import and attach resolvers to via @query.field / @mutation.field.
from .Query import query
from .Mutation import mutation
from .Sanscript import sanscriptSchemesEnum, dictionaryEnum, dictionaryItem
from .sans_parser import parseType, parseItemType  # also registers parser resolvers on `query`

type_defs = load_schema_from_path(os.path.dirname(os.path.abspath(__file__)))

type_resolvers = [query, mutation, dictionaryItem, parseType, parseItemType,
                  sanscriptSchemesEnum, dictionaryEnum]

schema = make_executable_schema(type_defs, type_resolvers)
