(:stream frontier-generates-place
  :inputs (?f)
  :domain (frontier ?f)
  :outputs (?p)
  :certified (and (place ?p) (connected ?f ?p)))

(:stream unobserved-place-generates-food
  :inputs (?p)
  :domain (and (place ?p) (not (observed ?p)))
  :outputs (?c)
  :certified (and (food ?c) (obj-at ?c ?p)))
