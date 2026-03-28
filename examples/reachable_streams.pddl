(:stream frontier-generates-place
  :inputs (?f - frontier)
  :domain ()
  :outputs (?p - place)
  :certified (connected ?f ?p))

(:derived frontier-connects-places
    :inputs (?p1 - place ?f - frontier ?p2 - place)
    :domain (and (connected ?p1 ?f) (connected ?f ?p2))
    :certified (connected ?p1 ?p2))

(:derived reachable-is-connected
    :inputs (?p1 - place ?p2 - place)
    :domain (connected ?p1 ?p2)
    :certified (reachable ?p1 ?p2))

(:derived transitive-reachable
    :inputs (?p1 - place ?p2 - place ?p3 - place)
    :domain (and (reachable ?p1 ?p2) (connected ?p2 ?p3))
    :certified (reachable ?p1 ?p3))
