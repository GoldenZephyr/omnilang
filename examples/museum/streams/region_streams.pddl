(:stream region-generates-place
  :inputs (?r - region)
  :domain (not (observed ?r))
  :outputs (?p - place)
  :certified (place-in-region ?p ?r))

(:stream unobserved-region-connections
  :inputs (?r1 - region ?r2 - region ?p1 - place ?p2 - place)
  :domain (and (region-connected ?r1 ?r2) (not (observed ?p1)) (not (observed ?p2)) (place-in-region ?p1 ?r1) (place-in-region ?p2 ?r2))
  :outputs ()
  :certified (connected ?p1 ?p2))

;; If the frontier generating a place is in region R, then so is the generated place
(:derived frontier-place-region-connection
    :inputs (?r - region ?f - frontier ?p - place)
    :domain (and (place-in-region ?f ?r) (connected ?f ?p) (not (observed ?p)))
    :certified (place-in-region ?p ?r))

(:derived check-region-observation
    :inputs (?r - region ?p - place)
    :domain (and (place-in-region ?p ?r) (observed ?p))
    :certified (observed ?r))

(:derived frontier-in-region
    :inputs (?r - region ?f - frontier ?p - place)
    :domain (and (place-in-region ?p ?r) (connected ?p ?f))
    :certified (place-in-region ?f ?r))
