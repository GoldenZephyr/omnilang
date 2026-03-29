import omnilang as oml
from omnilang import Symbol, Fact

# streams = parse_stream_file("streams.pddl")
# stream1 = streams[0]
# stream2 = streams[1]
# stream3 = streams[2]

facts = [
    Fact("frontier", [Symbol("f1")]),
    Fact("frontier", [Symbol("f2")]),
    Fact("place", [Symbol("p1")]),
    Fact("place", [Symbol("p2")]),
    Fact("place", [Symbol("p3")]),
    Fact("connected", [Symbol("p1"), Symbol("p2")]),
    Fact("connected", [Symbol("p1"), Symbol("f1")]),
    Fact("connected", [Symbol("f1"), Symbol("p3")]),
    Fact("observed", [Symbol("p1")]),
    Fact("at", [Symbol("p1")]),
]
s0 = oml.State(facts)


generated_symbols = oml.get_symbols_from_facts(s0.facts)
symbol_to_type = {}
symbol_to_type[Symbol("f1")] = "frontier"
symbol_to_type[Symbol("f2")] = "frontier"
symbol_to_type[Symbol("p1")] = "place"
symbol_to_type[Symbol("p2")] = "place"
symbol_to_type[Symbol("p3")] = "place"

env = oml.Environment(None, generated_symbols, symbol_to_type)

stream_path = "grounding_streams.pddl"
pddl_path = "domain_abstraction.pddl"
domain = oml.load_full_domain(pddl_path, stream_path)

stream = domain.derived_stream_facts[0]
print("Stream name: ", stream.name)
print("Formal Params: ", stream.formal_params)

bindings = []
for binding in oml.ground_with_domain(
    env, s0, stream.formal_params, stream.restrictions, stream.domain
):
    bindings.append(binding)
    print(binding)

print("Full bindings: ", bindings)

print("====== Negative Precondition Testing =====")
stream_path = "negative_grounding_streams.pddl"
domain = oml.load_full_domain(pddl_path, stream_path)

stream = domain.derived_stream_facts[0]
print("Stream name: ", stream.name)
print("Formal Params: ", stream.formal_params)


bindings = []
for binding in oml.ground_with_domain(
    env, s0, stream.formal_params, stream.restrictions, stream.domain
):
    bindings.append(binding)
    print(binding)

print("Full bindings: ", bindings)
