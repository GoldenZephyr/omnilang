(:derived frontier-connects-places
    :inputs (?p1 - place ?f - frontier ?p2 - place)
    :domain (and (connected ?p1 ?f) (connected ?f ?p2))
    :certified (connected ?p1 ?p2))
