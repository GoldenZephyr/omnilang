;; An unobserved place in a parking lot might have a cone
(:derived possibly-cone
    :inputs (?o - cone ?p - place ?r - parking)
    :domain (and (not (observed ?o)) (not (observed ?p)) (place-in-region ?p ?r))
    :certified (possibly-object ?o ?p))
