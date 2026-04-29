Streams
=======

```lisp
(:stream frontier-generates-place
  :inputs (?f - frontier)
  :domain ()
  :outputs (?p - place)
  :certified (connected ?f ?p))

(:derived frontier-connects-places
    :inputs (?p1 - place ?f - frontier ?p2 - place)
    :domain (and (connected ?p1 ?f) (connected ?f ?p2))
    :certified (and (connected ?p1 ?p2) (connected ?p2 ?p1)))

(:stream region-generates-place
  :inputs (?r - region)
  :domain (not (observed ?r))
  :outputs (?p - place)
  :certified (place-in-region ?p ?r))

(:stream unobserved-region-connections
  :inputs (?r1 - region ?r2 - region ?p1 - place ?p2 - place)
  :domain (and (region-connected ?r1 ?r2) (not (observed ?p1)) (not (observed ?p2)) (place-in-region ?p1 ?r1) (place-in-region ?p2 ?r2))
  :outputs ()
  :certified (connected ?p1 ?p2))

;; If the frontier generating a place is in region R, then so is the generated place
(:derived frontier-place-region-connection
    :inputs (?r - region ?f - frontier ?p - place)
    :domain (and (place-in-region ?f ?r) (connected ?f ?p) (not (observed ?p)))
    :certified (place-in-region ?p ?r))

(:derived check-region-observation
    :inputs (?r - region ?p - place)
    :domain (and (place-in-region ?p ?r) (observed ?p))
    :certified (observed ?r))

(:derived frontier-in-region
    :inputs (?r - region ?f - frontier ?p - place)
    :domain (and (place-in-region ?p ?r) (connected ?p ?f))
    :certified (place-in-region ?f ?r))

(:derived place-in-single-region
    :inputs (?p - place ?r1 - region ?r2 - region)
    :domain (and (place-in-region ?p ?r1) (place-in-region ?p ?r2) (!= ?r1 ?r2))
    :certified false)

(:stream generate-possible-object
  :inputs (?p - place)
  :domain (possibly-object ?o ?p)
  :outputs (?o - obj)
  :certified (obj-at ?o ?p))

;; An unobserved place in a parking lot might have a cone
(:derived possibly-cone
    :inputs (?o - cone ?p - place ?r - parking)
    :domain (and (not (observed ?o)) (not (observed ?p)) (place-in-region ?p ?r))
    :certified (possibly-object ?o ?p))
```

```lisp
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


    (:action pick
        :parameters (?o - obj ?p - place)
        :precondition (and (at ?p) (obj-at ?o ?p) (hand-free))
        :effect (and (not (obj-at ?o ?p)) (not (hand-free)) (holding ?o)))

    (:action place-obj
        :parameters (?o - obj ?p - place)
        :precondition (and (at ?p) (holding ?o))
        :effect (and (obj-at ?o ?p) (hand-free) (not (holding ?o))))

)
```


Goal
====

"All intersections should be blocked with a cone"

goal = oml.UniversalQuantifier(
    [oml.Symbol("?r")],
    ["intersection"],
    oml.ExistentialQuantifier(
        [oml.Symbol("?c")],
        ["cone"],
        oml.Fact("object-in-region", [oml.Symbol("?c"), oml.Symbol("?r")]),
    ),
)

Plan
====

('move-in-region', 't0', 't20', 'r0'),
('move-between-regions', 't20', 'r0', 't29', 'r3'),
('move-between-regions', 't29', 'r3', 't30', 'r4'),
('move-between-regions', 't30', 'r4', 'splace1', 'r4'),
('move-between-regions', 'splace1', 'r4', 'splace0', 'r7'),
('pick', 'scone0', 'splace0'),
('move-between-regions', 'splace0', 'r7', 'splace1', 'r4'),
('move-in-region', 'splace1', 't30', 'r4'),
('move-between-regions', 't30', 'r4', 't21', 'r1'),
('place-obj', 'scone0', 't21')
