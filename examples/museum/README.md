A bunch of examples of planning domains and stream definitions

Maps:
[x] 3x3 gridworld

[ ] 9x 3x3 gridworld with rooms

[ ] Uhumans office

[ ] Westpoint inspired 3D scene graph

Domain types:
[x] myopic

things to try in `simple_myopic`:
```
ipython3 -i grid_world.py -- observeall
ipython3 -i grid_world.py -- goto
ipython3 -i grid_world.py -- pickup
ipython3 -i grid_world.py -- getob
ipython3 -i grid_world.py -- getobj-easy
```

[x] search (shows groups)
[ ] search and pick (no groups)
[ ] search and pick (groups)
[ ] regions
[ ] searching regions
[ ] blocking intersections

Stream types:
[ ] frontier place stream
[ ] generic object
* efficient search object
* object in room
* dangerous rooms
* object inside openable object
* "maybe-connections" between predicted places


Directory per domain type
    Demo per env type
    Demo per relevant stream type
