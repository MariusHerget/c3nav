from c3nav.mapdata.models import Level, Package, Source
from c3nav.mapdata.models.collections import Elevator
from c3nav.mapdata.models.geometry import Building, Door, ElevatorLevel, Obstacle, Outside, Room

ordered_models = (Package, Level, Source, Building, Room, Outside, Door, Obstacle)
ordered_models += (Elevator, ElevatorLevel)
