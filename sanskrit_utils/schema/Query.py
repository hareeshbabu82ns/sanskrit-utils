from ariadne import ObjectType

query = ObjectType("Query")

@query.field("version")
def resolve_q_version(_, info):
    return info.context['apiVersion']