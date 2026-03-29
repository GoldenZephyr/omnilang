from omnilang.parse_goal import parse_goal_string

g1 = parse_goal_string("(at p1)")
print(g1)
g2 = parse_goal_string("(and (at p1) (holding o1))")
print(g2)
g3 = parse_goal_string("(or (at p1) (holding o1))")
print(g3)
g4 = parse_goal_string("(not (holding o1))")
print(g4)
g5 = parse_goal_string("(exists x (holding x))")
print(g5)
g6 = parse_goal_string("(exists x: (food x) (holding x))")
print(g6)
