(define (problem exploration_test_instance)
  (:domain exploration_test)

  (:objects
        f1 f2 - frontier
        p1 p2 p3 p4 p5 p6 - place
        o1 - obj
  )


  (:init
      (at p1)

      (visited p1)
      (visited p2)
      (visited p3)
      (visited p4)
      (visited p5)
      (visited p6)

      (hand-free)
      (obj-at o1 p1)

      (connected p6 f1)
      ;(connected p4 f2)
      ;(connected p1 f2)

      (connected p1 p2)
      (connected p2 p1)
      (connected p2 p3)
      (connected p3 p2)

      (connected p4 p5)
      (connected p5 p4)
      (connected p5 p6)
      (connected p6 p5)

      (connected p1 p4)
      (connected p4 p1)
      (connected p2 p5)
      (connected p5 p2)
      (connected p3 p6)
      (connected p6 p3)

  )

  ; (:goal (exists (?f - food) (holding ?f)))
  (:goal (forall (?p - place) (visited ?p)))
  ; (:goal (at p6))
  ; (:goal (forall (?p - place) (visited ?p)))

)
