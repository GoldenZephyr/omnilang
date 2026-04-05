(:stream generate-possible-object
  :inputs (?p - place)
  :domain (possibly-object ?o ?p)
  :outputs (?o - obj)
  :certified (obj-at ?o ?p))

(:derived possibly-food
    :inputs (?o - food ?p - place)
    :domain (and (not (observed ?o)) (not (observed ?p)))
    :certified (possibly-object ?o ?p))
