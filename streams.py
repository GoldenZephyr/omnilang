from testing import (
    Fact,
    Symbol,
    ground_predicate,
    ground,
    State,
    forall,
    Environment,
    ImproperQuantifiedSet,
    restrict,
    generate,
)
from dsg_pddl.pddl_grounding import PddlProblem, GroundedPddlProblem, PddlDomain
from dsg_pddl.pddl_planning import solve_pddl


def eval_quantifier(env, quantified_expression: ImproperQuantifiedSet, state: State):
    # TODO: currently state isn't used. It's not clear whether we should
    # restrict the domain to the symbols in env or re-extract the symbols in
    # state.
    # They mean slightly different things
    return restrict(
        env,
        quantified_expression,
        quantified_expression.unbound_symbols[0],
        env.symbols,
    )


def get_pddl_types(domain):
    # For these purposes, a type is a unary predicate that isn't present in any action effects
    # Or, I guess maybe we just read the type section from the domain?
    return ["place", "frontier", "obj"]


def group_objects_by_type(domain, facts):
    types = get_pddl_types(domain)
    type_to_objects = {}
    for f in facts:
        if f.head in types:
            if f.head not in type_to_objects:
                type_to_objects[f.head] = []
            type_to_objects[f.head].append(f.body[0])
    return type_to_objects


def group_facts_by_symbol(facts):
    symbol_to_facts = {}
    for f in facts:
        for s in f.body:
            if s.identifier not in symbol_to_facts:
                symbol_to_facts[s] = []
            symbol_to_facts[s].append(f)
    return symbol_to_facts


class SymbolMaker:
    key_to_index = {}

    @classmethod
    def get_identifier(cls, prefix=None):
        if prefix is None:
            prefix = "symbol"

        if prefix not in cls.key_to_index:
            cls.key_to_index[prefix] = 0

        identifier = f"{prefix}{cls.key_to_index[prefix]}"
        cls.key_to_index[prefix] += 1
        return Symbol(identifier)


class Stream:
    def __init__(
        self, params, domain, formal_outputs, certificates, symbol_prefixes=None
    ):
        self.formal_params = params  # List of symbols (formal params)
        self.domain = domain  # List of Restrictions
        self.formal_outputs = formal_outputs  # List of symbols
        self.certificates = certificates  # List of Restrictions
        if symbol_prefixes is None:
            self.symbol_prefixes = ["s" for _ in self.formal_outputs]
        else:
            assert len(symbol_prefixes) == len(self.formal_outputs)
            self.symbol_prefixes = symbol_prefixes

    def apply(self, args):
        assert len(args) == len(self.formal_params)

        grounded_outputs = [SymbolMaker.get_identifier(p) for p in self.symbol_prefixes]
        remapping = {o: g for o, g in zip(self.formal_outputs, grounded_outputs)}
        for o, a in zip(self.formal_params, args):
            remapping[o] = a
        grounded_facts = [ground_predicate(c, remapping) for c in self.certificates]
        return grounded_outputs, grounded_facts

    def get_applicable_args(self, symbols_to_facts):
        applicable_args = []
        for bindings in ground([[]], symbols_to_facts.keys()):
            current_facts = []
            for s in bindings:
                for f in symbols_to_facts[s]:
                    current_facts.append(f)
            satisfied = True
            r = {f: None for f in self.formal_params}
            for formal, val in zip(self.formal_params, bindings):
                r[formal] = val
            grounded_domain = [ground_predicate(d, r) for d in self.domain]
            for d in grounded_domain:
                if d not in current_facts:
                    satisfied = False
                    break
            if satisfied:
                applicable_args.append(bindings)
        return applicable_args


def add_facts_to_state(facts, state):
    # TODO: check for duplicates?
    return State(state.facts + facts)


def apply_transitive_frontier_rule(facts):
    connected_facts = [f for f in facts if f.head == "connected"]
    print("connected facts: ", connected_facts)
    frontiers = [f.body[0] for f in facts if f.head == "frontier"]
    print("frontiers: ", frontiers)

    def frontier_other_from_connected(fact):
        arg1_frontier = fact.body[0] in frontiers
        arg2_frontier = fact.body[1] in frontiers
        if arg1_frontier:
            if arg2_frontier:
                return None, None
            return fact.body[0], fact.body[1]
        if arg2_frontier:
            return fact.body[1], fact.body[0]
        return None, None

    for c1 in connected_facts:
        f1, o1 = frontier_other_from_connected(c1)
        for c2 in connected_facts:
            f2, o2 = frontier_other_from_connected(c2)
            if f1 == f2 and o1 != o2:
                new_connection = Fact("connected", [o1, o2])
                facts.append(new_connection)


def apply_rules(facts):
    # want to apply rule e.g. (connected p1 f1) (connected f1 p2) -> (connected p1 p2)
    # TODO: generalize...
    apply_transitive_frontier_rule(facts)


# A.) A stream representing "there might be a place next to a frontier"
S = Stream(
    [Symbol("?f")],
    [Fact("frontier", [Symbol("?f")])],
    ["?place"],
    [
        Fact("place", [Symbol("?place")]),
        Fact("connected", [Symbol("?f"), Symbol("?place")]),
    ],
    symbol_prefixes=["pred"],
)

original_symbols = [Symbol("f1"), Symbol("f2"), Symbol("o1"), Symbol("p1")]

facts = [
    Fact("frontier", [Symbol("f1")]),
    Fact("frontier", [Symbol("f2")]),
    Fact("place", [Symbol("p1")]),
    Fact("obj", [Symbol("o1")]),
    Fact("connected", [Symbol("f1"), Symbol("p1")]),
    Fact("connected", [Symbol("f2"), Symbol("p1")]),
]
state = State(facts)

SymbolMaker.key_to_index["p"] = 2

# symbols, new_facts = S.apply(facts[0])
symbols, new_facts = S.apply(["f1"])
print("Symbols from stream: ", symbols)


symbol_to_facts = group_facts_by_symbol(facts)

applicable_args = S.get_applicable_args(symbol_to_facts)
print("Applicable args: ", applicable_args)
print("Looping:")
symbols = original_symbols
for a in applicable_args:
    new_symbols, new_facts = S.apply(a)
    # print("Symbols from stream: ", symbols)
    # new_state = add_facts_to_state(new_facts, state)
    state = add_facts_to_state(new_facts, state)
    symbols = symbols + new_symbols

    # print("New state: ", new_state)
    # print("Symbols: ", symbols)
    # for f in new_state.facts:
    #    print(f)

for f in state.facts:
    print(f)


# B.) A rule that says "if frontier F is connected to both A and B, then A is connected to B
# This is necessary if we want to be able to apply a previously-constructed
# exploration domain to a new representation with frontiers.

apply_rules(state.facts)

print("Final facts:\n")
for f in state.facts:
    print(f)

print("Final symbols: ")
print(symbols)

objects = group_objects_by_type(None, state.facts)
init = state.facts
goal = forall("p", "place", Fact("visited", [Symbol("p")]))

type_to_objects = group_objects_by_type(None, state.facts)
symbol_to_type = {}
for k, v in type_to_objects.items():
    for val in v:
        symbol_to_type[val] = k
env = Environment(None, symbols, symbol_to_type)

evaled_goal = eval_quantifier(env, goal, state.facts)
print("evaled goal: ", evaled_goal)
print("Constituent facts: ")
for g in generate(evaled_goal):
    print(g)

init.append(Fact("at", [Symbol("p1")]))
init.append(Fact("visited", [Symbol("p1")]))

tuple_goal = ("and",) + tuple(a.to_tuple() for a in generate(evaled_goal))
with open("test_domain.pddl", "r") as fo:
    domain = PddlDomain(fo.read())

problem = PddlProblem(
    name="test_explore",
    domain="exploration_test",
    # TODO: "T" is temporary until we properly deal with types vs unary predicates
    objects={k + "T": [o.identifier for o in objs] for k, objs in objects.items()},
    initial_facts=[i.to_tuple() for i in init],
    goal=tuple_goal,
    optimizing=False,
)

problem_string = problem.to_string()

grounded_problem = GroundedPddlProblem(domain, problem_string, {})
plan = solve_pddl(grounded_problem)
print(plan)

# 4. "Feedforward TSP macroaction"
# 5. Abstractions from goal regression
# 6. Cleanup up demo
#   * Fully observed pick and place
#   * TSP macroaction

# Not yet addressed:
# * Theory / implementation for automatically determining that "explore all places" goal means that we need to run the streams
# * reordering to achieve cup pickup during TSP execution
# * Belief space planning for finding cup
