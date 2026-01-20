(define (domain exploration_test)

    (:types frontierT placeT objT foodT - object)
    (:functions )

    (:predicates
        (place ?p)
        (at ?p)
        (visited ?p)
        (connected ?p1 ?p2)
        (frontier ?f)
        (obj ?o)
        (obj-at ?o ?p)
        (hand-free)
        (holding ?o)
        (observed ?p)
        (food ?o)
    )

    (:action move
        :parameters (?s ?t)
        :precondition (and (at ?s) (connected ?s ?t))
        :effect (and (not (at ?s))
                     (at ?t)
                     (visited ?t)
                     (observed ?t)
        )
    )

    (:action pick
        :parameters (?o ?p)
        :precondition (and (at ?p) (obj-at ?o ?p) (hand-free))
        :effect (and (not (obj-at ?o ?p)) (not (hand-free)) (holding ?o)))

    (:action place-obj
        :parameters (?o ?p)
        :precondition (and (at ?p) (holding ?o))
        :effect (and (obj-at ?o ?p) (hand-free) (not (holding ?o))))

)
