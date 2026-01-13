(define (problem test_explore)
        (:domain exploration_test)
        (:objects
f1 f2 - frontierT
p1 pred1 pred2 - placeT
o1 - objT
)
        (:init
 (frontier f1)
(frontier f2)
(place p1)
(obj o1)
(connected f1 p1)
(place pred1)
(connected f1 pred1)
(place pred2)
(connected f2 pred2)
(connected p1 pred1)
(connected pred1 p1)
(at p1)
(visited p1) )
        (:goal (and (visited p1) (visited pred1) (visited pred2)))
        )