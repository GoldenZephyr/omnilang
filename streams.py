from testing import Fact, Symbol, ground_predicate, ground, State


def get_pddl_types(domain):
    # For these purposes, a type is a unary predicate that isn't present in any action effects
    # Or, I guess maybe we just read the type section from the domain?
    return ["Place", "frontier"]


def group_objects_by_type(domain, facts):
    types = get_pddl_types(domain)
    type_to_objects = {}
    for f in facts:
        if f.head in types:
            type_to_objects[f.head] = f.body[0]
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
    connected_facts = [f for f in facts if f.head == "Connected"]
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


S = Stream(
    [Symbol("?f")],
    [Fact("frontier", [Symbol("?f")])],
    ["?place"],
    [
        Fact("Place", [Symbol("?place")]),
        Fact("Connected", [Symbol("?f"), Symbol("?place")]),
    ],
    symbol_prefixes=["pred"],
)

original_symbols = [Symbol("f1"), Symbol("f2"), Symbol("o1")]

facts = [
    Fact("frontier", [Symbol("f1")]),
    Fact("frontier", [Symbol("f2")]),
    Fact("Place", [Symbol("p1")]),
    Fact("object", [Symbol("o1")]),
    Fact("Connected", [Symbol("f1"), Symbol("p1")]),
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
for a in applicable_args:
    symbols, new_facts = S.apply(a)
    # print("Symbols from stream: ", symbols)
    # new_state = add_facts_to_state(new_facts, state)
    state = add_facts_to_state(new_facts, state)
    symbols = original_symbols + symbols

    # print("New state: ", new_state)
    # print("Symbols: ", symbols)
    # for f in new_state.facts:
    #    print(f)

for f in state.facts:
    print(f)


apply_rules(state.facts)
print("Final facts:\n")
for f in state.facts:
    print(f)


objects = group_objects_by_type(None, state.facts)
init = state.facts
goal = forall("p", "Place", Fact("visited", Symbol("p")))
expanded_goal = expand_quantifiers(

problem = PddlProblem(
    name="test_explore",
    domain="exploration",
    objects=objects,
    initial_facts=init,
    goal=goal,
    optimizing=False,
)

problem_string = problem.to_string()
