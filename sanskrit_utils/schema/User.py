from ariadne import ObjectType
from sanskrit_utils.schema import query

user = ObjectType("User")

# Map resolvers to fields in Query type using decorator syntax...
@query.field("user")
def resolve_hello(_, info):
    return {'id': '33','name':'test'}