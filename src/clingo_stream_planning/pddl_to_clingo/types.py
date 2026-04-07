import omnilang as oml


def generate_type(type, supertype):
    return [f'type(type("{type}")).', f'inherits(type("{type}"), type("{supertype}")).']


def generate_type_hierarchy(env, domain: oml.FullDomain, state):
    lines = ["% types"]
    lines += ['type(type("object")).']
    for type, supertype in domain.pddl_domain.type_to_parent.items():
        lines += generate_type(type, supertype)
    lines.append("has(X, type(T2)) :- has(X, type(T1)), inherits(type(T1), type(T2)).")
    return lines
