from importlib.resources import as_file, files
import omnilang
from omnilang.mdp_definition import PddlDomain
from omnilang.mdp_states import Fact, NegatedFact, Symbol, TypedSymbol, negate
from omnilang.mdp_actions import LiftedAction
from lark import Lark, Transformer


# @dataclass
# class PddlDomain:
#    name: str
#    types: Optional[list[Predicate]]
#    functions: Optional[list]  # NOTE: we don't support functions yet
#    predicates: list[Predicate]
#    actions: list[LiftedAction]
#
#    def to_string(self):
#        return None


class DomainTransformer(Transformer):
    def start(self, domain):
        return domain

    def domain(self, items):
        name, fields = items
        types = fields[0]
        functions = fields[1]
        predicates = fields[2]
        actions = fields[3]
        return PddlDomain(name, types, functions, predicates, actions)

    def domain_body(self, items):
        types = None
        functions = None
        predicates = None
        actions = []
        for field, value in items:
            match field:
                case "types":
                    types = value
                case "functions":
                    functions = value
                case "predicates":
                    predicates = value
                case "action":
                    actions.append(value)
                case _:
                    raise ValueError(f"Unknown domain section {field}")
        return types, functions, predicates, actions

    def types(self, items):
        type_to_children = {}
        for t in items:
            type_to_children |= t
        return "types", type_to_children

    def type_decl(self, items):
        return {items[-1]: items[:-1]}

    def functions(self, items):
        return "functions", items

    def predicates(self, items):
        return "predicates", items

    def predicate_def(self, items):
        symbols = [item[0] for item in items[1:]]
        # restrictions = [item[1] for item in items[1:]] # TODO: do pass along restrictions
        return Fact(items[0], symbols)

    def action(self, items):
        name, parameters, precondition, effects = items
        params = [p[0] for p in parameters]
        restrictions = [p[1] for p in parameters]
        positive_effects = []
        negative_effects = []
        for f in effects:
            match f:
                case Fact():
                    positive_effects.append(f)
                case NegatedFact():
                    negative_effects.append(negate(f))
                case _:
                    raise Exception(f"Unknown action effect type {f})")
        return "action", LiftedAction(
            name, params, restrictions, precondition, positive_effects, negative_effects
        )

    def parameters(self, items):
        return items

    def precondition(self, items):
        return items[0]

    def effect(self, items):
        return items[0]

    def formula(self, items):
        return items[0]

    def conjunction(self, items):
        # TODO: eventually should explicitly represent conjunction
        return items

    def negation(self, items):
        match items[0]:
            case Fact():
                return negate(items[0])
            case NegatedFact():
                return negate(items[0])
            case _:
                raise ValueError(
                    f"Currently you can only negate facts, not formulas (tried to negate {items[0]}"
                )

    def atom(self, items):
        return Fact(items[0], items[1:])

    def taggable_var(self, items):
        match items[0]:
            case Symbol():
                return (items[0], [])
            case TypedSymbol():
                return (Symbol(items[0].identifier), items[0].type)
            case _:
                raise Exception(f"Unknown taggable_var {items[0]}")

    def typed_var(self, items):
        return TypedSymbol(items[0].identifier, items[1])

    def NAME(self, token):
        return str(token)

    def term(self, items):
        return items[0]

    def var(self, items):
        # Currently treat variables and nonvariables the same
        return Symbol(f"?{items[0]}")


def parse_domain_file(fn):
    with as_file(files(omnilang).joinpath("pddl_domain.lark")) as path:
        with open(path, "r") as fo:
            stream_grammar = fo.read()

    stream_parser = Lark(
        stream_grammar,
    )

    T = DomainTransformer()

    with open(fn, "r") as fo:
        streams = fo.read()

    tree = stream_parser.parse(streams)
    streams = T.transform(tree)
    return streams


if __name__ == "__main__":
    with open("pddl_domain.lark", "r") as fo:
        domain_grammar = fo.read()

    domain_parser = Lark(
        domain_grammar,
    )

    # T = StreamTransformer()

    # with open("streams.pddl", "r") as fo:
    #    example_streams = fo.read()

    # tree = stream_parser.parse(example_streams)
    # output = T.transform(tree)

    domain = parse_domain_file("pick_domain.pddl")
    print("Domain: ")
    print(domain)

    for a in domain.actions:
        print(a)
        print("")
