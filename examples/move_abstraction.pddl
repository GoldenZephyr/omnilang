(define (domain move_abstraction)

    (:types frontierT placeT objT splaceT - object)
    (:functions )

    (:predicates
        (place ?p)
        (splace ?p) ; set of places
        (at ?p)
        (visited ?p)
        (connected ?p1 ?p2)
        (frontier ?f)
        (obj ?o)
        (obj-at ?o ?p)
        (observed ?p)
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


    (:action observe-all
        :parameters (?places)
        :precondition (and (splace ?places))
        :effect (observed ?places))

    (:action find-obj
        :parameters (?o ?p ?places)
        :precondition (and (obj-at ?o ?p) (contains ?places ?p) (observed ?places))
        :effect (at ?p))

    ;(:action pick
    ;    :parameters (?o ?p)
    ;    :precondition (and (at ?p) (obj-at ?o ?p) (hand-free))
    ;    :effect (and (not (obj-at ?o ?p)) (not (hand-free)) (holding ?o)))

    ;(:action place-obj
    ;    :parameters (?o ?p)
    ;    :precondition (and (at ?p) (holding ?o))
    ;    :effect (and (obj-at ?o ?p) (hand-free) (not (holding ?o))))

)
