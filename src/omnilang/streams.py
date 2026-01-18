# ruff: noqa: F811
from omnilang.mdp_states import (
    Symbol,
    ground_predicate,
    ground,
    State,
    ImproperQuantifiedSet,
    restrict,
    Environment,
    Fact,
    PartialState,
)
from plum import dispatch


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
            if f.body[0] not in type_to_objects[f.head]:
                type_to_objects[f.head].append(f.body[0])
    return type_to_objects


def get_symbol_to_type(domain, state):
    type_to_objects = group_objects_by_type(domain, state.facts)
    symbol_to_type = {}
    for k, v in type_to_objects.items():
        for val in v:
            symbol_to_type[val] = k
    return symbol_to_type


def group_facts_by_symbol(facts):
    symbol_to_facts = {}
    for f in facts:
        for s in f.body:
            if s.identifier not in symbol_to_facts:
                symbol_to_facts[s] = []
            symbol_to_facts[s].append(f)
    return symbol_to_facts


def get_symbols_from_facts(facts: list[Fact]):
    symbols = set()
    for f in facts:
        for arg in f.body:
            symbols.add(arg)
    return symbols


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
        self, name, params, domain, formal_outputs, certificates, symbol_prefixes=None
    ):
        self.name = name
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


@dispatch
def extract_goal_predicates(goal: PartialState):
    positive_heads = [f.head for f in goal.positive_facts]
    negative_heads = [f.head for f in goal.negative_facts]
    return positive_heads + negative_heads


@dispatch
def extract_goal_predicates(goal: ImproperQuantifiedSet):
    # TODO: may also need to support QuantifiedSet? And State/PartialState?
    # TODO: This will need to generalize when we consider more complicated goals
    example_fact = goal.transformation(None, Symbol("x"))
    return [example_fact.head]


@dispatch
def does_goal_depend_on(goal: ImproperQuantifiedSet, env, symbol):
    return goal.element_filter(env, symbol)


@dispatch
def does_goal_depend_on(goal: PartialState, env, symbol):
    goal_symbols = get_symbols_from_facts(goal.positive_facts | goal.negative_facts)
    return symbol in goal_symbols


def find_streams_affecting_goal(streams: set[Stream], state: State, goal):
    # first do the easy check, whether any stream outputs overlap with goal facts
    # If this is not the case, then we can return an empty set of streams
    # This takes care of goals where there are no relevant streams
    # Otherwise, we do a relaxed reachability check between the initial state and the goal
    # If this relaxed check fails, then there are no relevant streams
    # NOTE: skipped the above, should be subsumed by check below (?)

    # If the previous check succeeded, then return all streams that are on *a*
    # path from the initial state to the goal
    predicates_in_goal = extract_goal_predicates(goal)
    print("preds in goal: ", predicates_in_goal)

    name_to_stream = {s.name: s for s in streams}
    direct_dependencies = {s.name: set() for s in streams}
    direct_dependencies["goal"] = set()
    bindable = {s.name: False for s in streams}

    state_predicates = [s.head for s in state.facts]

    for s in streams:
        stream_domain_predicates = {f.head for f in s.domain}
        unsatisfied_predicates = {f.head for f in s.domain}
        for dp in stream_domain_predicates:
            if dp in state_predicates:
                unsatisfied_predicates.remove(dp)

        for t in streams:
            output_predicates = [f.head for f in t.certificates]
            for op in output_predicates:
                if op in stream_domain_predicates:
                    direct_dependencies[s.name].add(t.name)

        if len(unsatisfied_predicates) == 0:
            bindable[s.name] = True

    # check which streams the goal depends on *directly*
    for t in streams:
        # TODO: feed in domain
        domain = None
        symbol_to_type = get_symbol_to_type(domain, State(t.certificates))
        print(f"Stream {t.name} output types: {symbol_to_type}")
        # TODO: parent env
        child_env = Environment(None, t.formal_outputs, symbol_to_type)

        # TODO: handle streams with multiple outputs
        if does_goal_depend_on(goal, child_env, Symbol(t.formal_outputs[0])):
            direct_dependencies["goal"].add(t.name)

    # Now, we want all satisfied streams that are backwards-reachable from goal
    expanded = True
    reachable_stream_set = direct_dependencies["goal"]
    while expanded:
        expanded = False
        for s in reachable_stream_set:
            for t in direct_dependencies[s]:
                if not bindable[t]:
                    continue
                if t in reachable_stream_set:
                    continue
                reachable_stream_set.add(t)
                expanded = True

    return set(name_to_stream[s] for s in reachable_stream_set)


def add_facts_to_state(facts, state):
    # TODO: Deal with duplicates and negations?
    return State(state.facts + facts)


def expand_streams(env, streams, state):
    # compose (\circ) streams (in the order given) to state
    # Actually, this is not exactly \circ, because here we apply each stream as
    # many times as possible at the current depth before moving on to the next
    # stream

    # TODO: also need to return *new environment*
    new_symbols = []
    new_symbols_to_type = {}
    for s in streams:
        symbol_to_facts = group_facts_by_symbol(state.facts)
        applicable_args = s.get_applicable_args(symbol_to_facts)
        for a in applicable_args:
            ns, new_facts = s.apply(a)

            domain = None
            new_symbols_to_type |= get_symbol_to_type(domain, State(new_facts))

            state = add_facts_to_state(new_facts, state)
            new_symbols = new_symbols + ns

    new_env = Environment(env, new_symbols, new_symbols_to_type)

    return new_env, state


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
