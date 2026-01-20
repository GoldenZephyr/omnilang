(:stream dummy-stream
  :inputs (?g)
  :domain (DNE ?g)
  :outputs (?widget)
  :certified (and (shoe ?widget) (on ?g ?shoe)))

(:stream frontier-generates-place
  :inputs (?f)
  :domain (frontier ?f)
  :outputs (?p)
  :certified (and (place ?p) (connected ?f ?p)))


;(:stream dummy-frontier-generator
;  :inputs (?o)
;  :domain (objet ?o)
;  :outputs (?f)
;  :certified (and (frontier ?f) (connected ?o ?f)))
