from ariadne import ObjectType

mutation = ObjectType("Mutation")

@mutation.field("version")
def resolve_m_version(_, info):
    return info.context['apiVersion']