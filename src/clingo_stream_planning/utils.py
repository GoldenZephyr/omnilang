import omnilang as oml


def pddl_problem_to_state(problem: oml.PddlProblemInstance, types):
    s0 = oml.State(set(problem.initial_facts))
    symbols = problem.objects
    symbol_to_type = problem.objects_to_type
    return s0, oml.Environment(None, symbols, symbol_to_type, types)
