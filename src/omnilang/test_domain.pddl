(define (domain exploration_test)

    (:types frontierT placeT objT - object)
    (:functions )

    (:predicates
        (place ?p)
        (at ?p)
        (visited ?p)
        (connected ?p1 ?p2)
        (frontier ?f)
        (obj ?o)
    )

    (:action move
        :parameters (?s ?t)
        :precondition (and (at ?s) (connected ?s ?t))
        :effect (and (not (at ?s))
                     (at ?t)
                     (visited ?t)
        )
    )

)
