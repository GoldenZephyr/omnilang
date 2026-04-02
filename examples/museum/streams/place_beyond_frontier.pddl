(:stream frontier-generates-place
  :inputs (?f - frontier)
  :domain ()
  :outputs (?p - place)
  :certified (connected ?f ?p))

(:derived frontier-connects-places
    :inputs (?p1 - place ?f - frontier ?p2 - place)
    :domain (and (connected ?p1 ?f) (connected ?f ?p2))
    :certified (and (connected ?p1 ?p2) (connected ?p2 ?p1)))
