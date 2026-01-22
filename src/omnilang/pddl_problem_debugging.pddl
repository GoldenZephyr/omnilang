(define (problem test_explore)
        (:domain move_abstraction)
        (:objects
o1 - objT
p1 p2 - placeT
q1 - splaceT
f2 f1 - frontierT
)
        (:init
 (obj o1)
(connected p2 p1)
(place p1)
(connected f1 p1)
(connected f2 p1)
(splace q1)
(frontier f2)
(connected p1 p2)
(place p2)
(frontier f1)
(at p1)
(visited p1) )
        (:goal (and (observed q1)))
        )