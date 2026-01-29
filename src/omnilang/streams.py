# ruff: noqa: F811
from omnilang.mdp_states import (
    Symbol,
    State,
    ImproperQuantifiedSet,
    Fact,
    NegatedFact,
    PartialState,
    negate,
)
from omnilang.environment import Environment
from omnilang.mdp_state_operations import ground, ground_predicate, restrict
from plum import dispatch
from math import inf
from dataclasses import dataclass


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
    return ["place", "frontier", "obj", "food", "mold", "splace"]


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


@dispatch
def consistent_with(f: Fact, current_facts: list[Fact]):
    return f in current_facts


@dispatch
def consistent_with(f: NegatedFact, current_facts: list[Fact]):
    return negate(f) not in current_facts


@dataclass(frozen=True)
class GroundedStream:
    name: str
    inputs: tuple[Symbol]
    output_symbols: tuple[Symbol]
    output_facts: tuple[Fact]


class Stream:
    def __init__(
        self,
        name,
        params,
        domain,
        formal_outputs,
        certificates,
        symbol_prefixes=None,
        metadata_generator=None,
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

        self.metadata_generator = metadata_generator

    def apply(self, args, environment=None, grounded_outputs=None):
        """grounded_outputs can be passed as an input if it's necessary to make
        the stream's output be consistent across multiple applications, e.g.,
        when reapplying a stream to an updated base environment"""

        assert len(args) == len(self.formal_params)

        if grounded_outputs is None:
            grounded_outputs = [
                SymbolMaker.get_identifier(p) for p in self.symbol_prefixes
            ]

        remapping = {o: g for o, g in zip(self.formal_outputs, grounded_outputs)}
        for o, a in zip(self.formal_params, args):
            remapping[o] = a
        grounded_facts = [ground_predicate(c, remapping) for c in self.certificates]
        metadata = self.generate_metadata(environment, args, grounded_outputs)

        return GroundedStream(
            self.name, tuple(args), tuple(grounded_outputs), tuple(grounded_facts)
        ), metadata
        # return grounded_outputs, grounded_facts, metadata

    def generate_metadata(self, environment, inputs, output_args):
        print(
            "generate_metadata symbols with position: ",
            environment.get_symbols_with_metadata("position"),
        )
        print("generated_metadata g0: ", environment.get_metadata_for_symbol("g0"))
        if self.metadata_generator is not None:
            if environment is not None:
                print("getting metadata for inputs: ", inputs)
                metadata = self.metadata_generator(
                    *[environment.get_metadata_for_symbol(s.identifier) for s in inputs]
                )
            else:
                metadata = self.metadata_generator(*[{} for s in inputs])
        else:
            metadata = [{} for _ in output_args]
        return {k: v for k, v in zip(output_args, metadata)}

    def is_applicable(self, args, symbols_to_facts):
        current_facts = []
        for s in args:
            if s in symbols_to_facts:
                for f in symbols_to_facts[s]:
                    current_facts.append(f)
        print("current_facts", current_facts)
        satisfied = True
        r = {f: None for f in self.formal_params}
        for formal, val in zip(self.formal_params, args):
            r[formal] = val
        grounded_domain = [ground_predicate(d, r) for d in self.domain]
        for d in grounded_domain:
            print("checking consistency for :", d)
            if not consistent_with(d, current_facts):
                satisfied = False
                break

        return satisfied

    def get_applicable_args(self, symbols_to_facts):
        print("\nGetting applicable args for ", self.name)
        applicable_args = []
        for bindings in ground([[]], symbols_to_facts.keys()):
            print("checking bindings ", bindings)
            current_facts = []
            for s in bindings:
                for f in symbols_to_facts[s]:
                    current_facts.append(f)
            print("current_facts", current_facts)
            satisfied = True
            r = {f: None for f in self.formal_params}
            for formal, val in zip(self.formal_params, bindings):
                r[formal] = val
            grounded_domain = [ground_predicate(d, r) for d in self.domain]
            for d in grounded_domain:
                print("checking consistency for :", d)
                if not consistent_with(d, current_facts):
                    satisfied = False
                    break
            if satisfied:
                print("Added binding ", bindings)
                applicable_args.append(bindings)
        print("Final applicable args: ", applicable_args)
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
    new_reachable_streams = direct_dependencies["goal"]
    reachable_stream_set = set()
    while len(new_reachable_streams) > 0:
        reachable_stream_set |= new_reachable_streams
        new_reachable_streams = set()
        for s in reachable_stream_set:
            for t in direct_dependencies[s]:
                if not bindable[t]:
                    continue
                if t in reachable_stream_set or t in new_reachable_streams:
                    continue
                new_reachable_streams.add(t)

    return set(name_to_stream[s] for s in reachable_stream_set)


def add_facts_to_state(facts, state):
    # TODO: Deal with duplicates and negations?
    return State(state.facts | set(facts))


def expand_streams(env, streams, state, stream_evals_per_level=inf):
    # compose (\circ) streams (in the order given) to state
    # Actually, this is not exactly \circ, because here we apply each stream as
    # many times as possible at the current depth before moving on to the next
    # stream

    new_symbols = ()
    new_symbols_to_type = {}
    new_symbol_metadata = []
    for s in streams:
        symbol_to_facts = group_facts_by_symbol(state.facts)
        applicable_args = s.get_applicable_args(symbol_to_facts)
        for idx, a in enumerate(applicable_args):
            # NOTE: implications for passing base env to all streams (vs. "incrementally" updated env)
            print(f"Applying stream {s.name} with args:", a)
            grounded_stream, symbol_metadata = s.apply(a, environment=env)

            ns = grounded_stream.output_symbols
            new_facts = grounded_stream.output_facts
            for m in symbol_metadata.values():
                m["generator"] = grounded_stream

            new_symbol_metadata.append(symbol_metadata)

            domain = None
            new_symbols_to_type |= get_symbol_to_type(domain, State(new_facts))

            state = add_facts_to_state(new_facts, state)
            new_symbols = new_symbols + ns
            if idx >= stream_evals_per_level:
                break

    new_env = Environment(env, new_symbols, new_symbols_to_type)
    print("new symbol metadata: ", new_symbol_metadata)
    for nsm in new_symbol_metadata:
        for s, m in nsm.items():
            new_env.attach_metadata(s.identifier, m)

    return new_env, state
