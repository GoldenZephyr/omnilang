(:stream unobserved-place-generates-food
  :inputs (?p - place)
  :domain (not (observed ?p))
  :outputs (?c - food)
  :certified (obj-at ?c ?p))
