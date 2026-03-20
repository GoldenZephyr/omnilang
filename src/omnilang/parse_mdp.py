from importlib.resources import as_file, files
import omnilang.lark
from omnilang.mdp_definition import PddlDomain, DomainPredicate, PddlProblemInstance
from omnilang.mdp_states import (
    Fact,
    NegatedFact,
    Symbol,
    TypedSymbol,
    negate,
    PddlExists,
    PddlForall,
    PartialState,
)
from omnilang.mdp_actions import LiftedAction
from lark import Lark, Transformer


class ProblemTransformer(Transformer):
    def start(self, domain):
        return domain

    def problem(self, items):
        name, fields = items
        domain = fields[0]
        objects, objects_to_type, type_to_objects = fields[1]
        init = fields[2]
        goal = fields[3]

        return PddlProblemInstance(
            name, domain, objects, objects_to_type, type_to_objects, init, goal
        )

    def problem_body(self, items):
        return items

    def domain(self, items):
        return items[0]

    def objects(self, instances_of_type: list[tuple[str, list[Symbol]]]):
        objects = []
        type_to_objects = {}
        objects_to_type = {}
        for type, symbols in instances_of_type:
            objects += symbols
            type_to_objects[type] = symbols
            for s in symbols:
                objects_to_type[s] = type
        return objects, objects_to_type, type_to_objects

    def instances_of_type(self, items):
        type = items[1]
        instances = items[0]
        return type, instances

    def init(self, items):
        return items

    def fact(self, items):
        head, body = items
        return Fact(head, body)

    def lifted_fact(self, items):
        head, body = items
        return Fact(head, body)

    def symbol_list(self, items):
        return items

    def symbol(self, items):
        return Symbol(items[0])

    def goal(self, item):
        print(item)
        match item[0]:
            case PddlExists() | PddlForall():
                return item[0]
            case _:
                return PartialState(set(item), set())

    def formula(self, items):
        return items[0]

    def conjunction(self, items):
        # TODO: eventually should explicitly represent conjunction
        return PartialState(set(items), set())

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

    def disjunction(self, items):
        raise NotImplementedError("Disjunctive goals not yet supported!")

    def universal(self, items):
        args, body = items
        types = []
        formal_args = []
        for a in args:
            formal_args.append(a[0])
            match a:
                case (_, type):
                    types.append(type)
                case (_, []):
                    types.append("object")
        return PddlForall(formal_args, types, body)

    def existential(self, items):
        args, body = items
        types = []
        formal_args = []
        for a in args:
            formal_args.append(a[0])
            match a:
                case (_, type):
                    types.append(type)
                case (_, []):
                    types.append("object")
        return PddlExists(formal_args, types, body)

    def taggable_var(self, items):
        match items[0]:
            case Symbol():
                return (items[0], [])
            case TypedSymbol():
                return (Symbol(items[0].identifier), items[0].type)
            case _:
                raise Exception(f"Unknown taggable_var {items[0]}")

    def taggable_var_list(self, items):
        return items

    def typed_var(self, items):
        return TypedSymbol(items[0].identifier, items[1])

    def NAME(self, token):
        return str(token)

    def var(self, items):
        # Currently treat variables and nonvariables the same
        return Symbol(f"?{items[0]}")

    def var_list(self, items):
        return items


def is_group_action(action: LiftedAction):
    return any(s.identifier.startswith("&") for s in action.params)


class DomainTransformer(Transformer):
    def start(self, domain):
        return domain

    def domain(self, items):
        name, fields = items
        types = fields[0]
        functions = fields[1]
        predicates = fields[2]
        actions = fields[3]
        group_actions = fields[4]
        requirements = fields[5]
        return PddlDomain(
            name,
            types,
            functions,
            predicates,
            actions,
            requirements,
            group_actions=group_actions,
        )

    def domain_body(self, items):
        types = None
        functions = None
        predicates = None
        requirements = None
        actions = []
        group_actions = []
        for field, value in items:
            match field:
                case "types":
                    types = value
                case "functions":
                    functions = value
                case "predicates":
                    predicates = value
                case "action":
                    if is_group_action(value):
                        group_actions.append(value)
                    else:
                        actions.append(value)
                case "requirements":
                    requirements = value
                case _:
                    raise ValueError(f"Unknown domain section {field}")
        return types, functions, predicates, actions, group_actions, requirements

    def types(self, items):
        type_to_children = {}
        for t in items:
            type_to_children |= t
        return "types", type_to_children

    def requirements(self, items):
        return "requirements", items

    def requirement(self, items):
        return str(items[0])

    def type_decl(self, items):
        return {items[-1]: items[:-1]}

    def functions(self, items):
        return "functions", items

    def predicates(self, items):
        return "predicates", items

    def predicate_def(self, items):
        symbols = [item[0] for item in items[1:]]
        restrictions = [[item[1]] if item[1] is not None else [] for item in items[1:]]
        return DomainPredicate(items[0], symbols, restrictions)

    def action(self, items):
        name, parameters, precondition, effects = items
        params = [p[0] for p in parameters]
        restrictions = [[p[1]] if p[1] is not None else [] for p in parameters]
        positive_effects = []
        negative_effects = []
        match effects:
            case tuple() | list():
                for f in effects:
                    match f:
                        case Fact():
                            positive_effects.append(f)
                        case NegatedFact():
                            negative_effects.append(negate(f))
                        case _:
                            raise Exception(f"Unknown action effect type {f})")
            case Fact():
                positive_effects.append(effects)
            case NegatedFact():
                negative_effects.append(effects)
            case _:
                raise ValueError(
                    f"Unexpected effect type {type(effects)} for {effects}"
                )

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
                return (items[0], None)
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

    def group_var(self, items):
        return Symbol(f"&{items[0]}")


def parse_domain_file(fn):
    with as_file(files(omnilang.lark).joinpath("pddl_domain.lark")) as path:
        with open(path, "r") as fo:
            domain_grammar = fo.read()

    domain_parser = Lark(
        domain_grammar,
    )

    T = DomainTransformer()

    with open(fn, "r") as fo:
        streams = fo.read()

    tree = domain_parser.parse(streams)
    domain = T.transform(tree)
    return domain


def parse_problem_file(fn):
    with as_file(files(omnilang.lark).joinpath("pddl_instance.lark")) as path:
        with open(path, "r") as fo:
            problem_grammar = fo.read()

    problem_parser = Lark(
        problem_grammar,
    )

    T = ProblemTransformer()

    with open(fn, "r") as fo:
        problem = fo.read()

    tree = problem_parser.parse(problem)
    problem = T.transform(tree)
    return problem


if __name__ == "__main__":
    domain = parse_domain_file("pick_domain.pddl")
    print("Domain: ")
    print(domain)

    for a in domain.actions:
        print(a)
        print("")
