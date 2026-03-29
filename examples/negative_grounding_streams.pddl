(:derived maybe-food
    :inputs (?p1 - place)
    :domain (not (observed ?p1))
    :certified (maybe-food ?p1))
