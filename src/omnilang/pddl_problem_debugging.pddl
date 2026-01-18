(define (problem test_explore)
        (:domain exploration_test)
        (:objects
o0 o1 - objT
f0 - frontierT
t0 t1 - placeT
)
        (:init
 (obj o0)
(obj o1)
(frontier f0)
(connected f0 t1)
(place t0)
(connected t0 t1)
(place t1)
(connected t1 t0)
(at t0)
(visited t0) )
        (:goal (and (visited t1) (visited t0)))
        )