(define (problem test_explore)
        (:domain exploration_test)
        (:objects
f0 - frontierT
t1 t0 s4 - placeT
s3 - foodT
O0 O1 - objT
)
        (:init
 (at t0)
(connected f0 t1)
(frontier f0)
(visited t0)
(connected f0 s4)
(connected t1 t0)
(connected t1 s4)
(place t1)
(connected s4 t1)
(obj-at O1 t1)
(obj-at s3 t1)
(place t0)
(place s4)
(observed t0)
(food s3)
(obj O0)
(obj-at O0 t0)
(obj O1)
(connected t0 t1) )
        (:goal (or (obj-at s3 t0)))
        )