(define (domain westpoint_domain)
    (:requirements :adl :typing)

    (:types obj region location - object
            frontier place - location
            parking intersection - region
            cone mallet box food - obj)

    (:predicates
        (at ?p - place)
        (visited ?p - place)
        (connected ?p1 - location ?p2 - location)
        (frontier ?f - frontier)
        (obj-at ?o - obj ?p - place)
        (hand-free)
        (holding ?o - obj)
        (observed ?p - object)
        (known-location ?o - obj)
        (reachable ?s - place ?t - place)
        (group ?g - object)
        (place-in-region ?p - location ?r - region)
        (object-in-region ?o - obj ?r - region)
        (in-region ?r - region)
        (region-connected ?r1 - region ?r2 - region)
        (searched-region ?r - region)
    )

    (:derived (in-region ?r)
        (exists (?p - place) (and (at ?p) (place-in-region ?p ?r))))

    (:derived (object-in-region ?o ?r)
        (exists (?p - place) (and (place-in-region ?p ?r) (obj-at ?o ?p))))

    (:derived (searched-region ?r)
        (forall (?p - place) (implies (place-in-region ?p ?r) (observed ?p))))


    (:action move-in-region
        :parameters (?s - place ?t - place ?r - region)
        :precondition (and (at ?s) (place-in-region ?s ?r) (place-in-region ?t ?r))
        :effect (and (not (at ?s))
                     (at ?t)
                     (visited ?t)
                     (observed ?t)
        )
    )

    (:action move-between-regions
        :parameters (?s - place ?r1 - region ?t - place ?r2 - region)
        :precondition (and (at ?s) (connected ?s ?t) (place-in-region ?s ?r1) (place-in-region ?t ?r2))
        :effect (and (not (at ?s))
                     (at ?t)
                     (visited ?t)
                     (observed ?t)
        )
    )

    ;(:action movegroup
    ;    :parameters (?s - place &g - location)
    ;    :precondition (and (at ?s)
    ;                       (not (visited &g))
    ;                  )
    ;    :effect (and (visited &g)
    ;                 (observed &g)
    ;    )
    ;)


    ;(:action pick
    ;    :parameters (?o - obj ?p - place)
    ;    :precondition (and (known-location ?o) (at ?p) (obj-at ?o ?p) (hand-free))
    ;    :effect (and (not (obj-at ?o ?p)) (not (hand-free)) (holding ?o)))


    (:action pick
        :parameters (?o - obj ?p - place)
        :precondition (and (at ?p) (obj-at ?o ?p) (hand-free))
        :effect (and (not (obj-at ?o ?p)) (not (hand-free)) (holding ?o)))

    (:action place-obj
        :parameters (?o - obj ?p - place)
        :precondition (and (at ?p) (holding ?o))
        :effect (and (obj-at ?o ?p) (hand-free) (not (holding ?o))))

)
