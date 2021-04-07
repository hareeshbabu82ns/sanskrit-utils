from ariadne import gql, load_schema_from_path, make_executable_schema
from ariadne import ObjectType
import flask

from .Query import query
from .Mutation import mutation
from .User import user
from .Sanscript import sanscriptSchemesEnum, dictionaryEnum

type_defs = load_schema_from_path("sanskrit_utils/schema")

type_resolvers = [query, mutation, user, sanscriptSchemesEnum, dictionaryEnum]

schema = make_executable_schema(type_defs, type_resolvers)
