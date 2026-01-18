(define (domain exploration_test)

    (:types frontierT placeT objT - object)
    (:functions )

    (:predicates
        (place ?p)
        (at ?p)
        (visited ?p)
        (connected ?p1 ?p2)
        (frontier ?f) ; test comment
        (obj ?o)
    )

    (:action move
        :parameters (?p1 ?p2)
        :precondition (and (at ?p1) (connected ?p1 ?p2))
        :effect (and (not (at ?p1))
                     (at ?p2)
        )
    )

)
