(define (domain myopic_pick)
    (:requirements :adl :typing)

    (:types obj location - object
            frontier place - location
            box food - obj)

    (:predicates
        (at ?p - place)
        (visited ?p - place)
        (connected ?p1 - location ?p2 - location)
        (frontier ?f - frontier)
        (obj-at ?o - obj ?p - place)
        (hand-free)
        (holding ?o - obj)
        (observed ?p - place)
    )

    (:action move
        :parameters (?s - place ?t - place)
        :precondition (and (at ?s) (connected ?s ?t))
        :effect (and (not (at ?s))
                     (at ?t)
                     (visited ?t)
                     (observed ?t)
        )
    )

    (:action pick
        :parameters (?o - obj ?p - place)
        :precondition (and (at ?p) (obj-at ?o ?p) (hand-free))
        :effect (and (not (obj-at ?o ?p)) (not (hand-free)) (holding ?o)))

    (:action place-obj
        :parameters (?o - obj ?p - place)
        :precondition (and (at ?p) (holding ?o))
        :effect (and (obj-at ?o ?p) (hand-free) (not (holding ?o))))

)
