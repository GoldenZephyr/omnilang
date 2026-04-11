# Proposal for better way of associating objects to groups.
# Identifying the groups by collections of predicates
# makes remapping after world updates much more sane.

# p1.
# p2.
# r1.
# r2.
# g1.
# group(g1).
#
# w0(("place-in-region", p1, r1)).
# w0(("place-in-region", p2, r1)).
# w0(("place-in-region", p3, r2)).
#
# ingroup(G, L) :- group_chosen(G, (P, X1), 1), w0((P, L, X1)).
# ingroup(G, L) :- group_chosen(G, (P, X1), 2), w0((P, X1, L)).
#
# group_chosen(g1, ("place-in-region", r1), 1).
