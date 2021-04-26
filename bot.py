import sys
import random
import time
from math import sqrt
import datetime
from dataclasses import dataclass
from operator import attrgetter
import functools

class param:
    distance = 1
    prod = 2
    ships = 1
    enemy = 2
    protag = 1
    aggression_prod = 2
    aggression_ships = 1
    threshold = 200

def bot(galaxy):

    start_time = datetime.datetime.now()
    print(galaxy)

    # protag means ourself
    protag = galaxy.protag # ourselfves
    enemy = galaxy.enemy
    neutral = galaxy.neutral

    all_planets = galaxy.planets
    other_planets = PlanetGroup(enemy.planets + neutral.planets)

    if len(all_planets) == 0 or len(protag.planets) == 0 or len(protag.planets) == len(all_planets):
        return

    source = protag.planets.find_max('ships')

    for planet in galaxy.planets:
        planet.score = sum([
            300,
            planet.prod * param.prod,
            - param.distance * source.distance_to(planet),
            - param.ships * planet.ships * param.ships,
        ])

        if planet.owner == enemy:
            planet.score *= param.enemy

        if planet.owner == protag:
            planet.score -= param.protag * abs(planet.score)

    target_candidate = other_planets.find_max('score')

    aggression = product(
        100 + param.aggression_prod,
        (enemy.prod - protag.prod) + param.aggression_ships,
        (protag.ships - enemy.ships)
    )

    conditions = [
        (protag.prod - enemy.prod) + 4 * (protag.ships - enemy.ships) > 1000,
        target_candidate.score * aggression > param.threshold
    ]

    if any(conditions):
        source.send(70, target_candidate)

    print("Took", str((datetime.datetime.now() - start_time).microseconds), "microseconds")

########################################################################################

class PlanetGroup(list):
    @property
    def prod(self):
        return sum([p.prod for p in self])
    def find_max(self, attr):
        return max(self, key=attrgetter(attr))


class FleetGroup(list):
    @property
    def ships(self):
        return sum([fleet.ships for fleet in self])

class Galaxy():
    def __init__(self, users, planets: PlanetGroup, fleets: FleetGroup):
        self.users = users
        self.planets = planets
        self.fleets = fleets
        self.protag = {user.name: user for user in users}['one']
        self.neutral = {user.name: user for user in users}['neutral']
        self.enemy = [user for user in users if user.name not in [self.neutral.name, self.protag.name]].pop()

    def __repr__(self):
        ret = "GALAXY:\n"
        ret += " protag: " + str(self.protag) + '\n'
        ret += " enemy: " + str(self.enemy) + '\n'
        ret += " neutral: " + str(self.neutral) + '\n'
        ret += ' users:\n'
        for user in self.users:
            ret += "  " + str(user) + '\n'
            for planet in user.planets:
                ret += '   ' + str(planet) + '\n'
        ret += ' fleets:\n'
        for fleet in self.fleets:
            ret += "  " + str(fleet) + '\n'
        return ret

@dataclass
class Position:
    x: float
    y: float
    def __repr__(self):
        return "[x:" + str(self.x) + " y:" + str(self.y) + ']'

class User():
    def __init__(self, n: int, xid: int, name: str, color: int, team: int):
        self.n = n
        self.name = name
        self.color = color
        self.team = team
        self.xid = xid

        self.planets = PlanetGroup()
        self.fleets = FleetGroup()
    @property
    def prod(self):
        return sum([planet.prod for planet in self.planets])
    @property
    def ships(self):
        return sum([planet.ships for planet in self.planets]) + sum([fleet.ships for fleet in self.fleets])

    def __repr__(self):

        return "user['" + self.name + "' planets:" + str(len(self.planets)) + " total_prod:" + str(self.planets.prod) + " n:" + str(self.n) + ']'

class Planet():
    def __init__(self, n: int, owner: User, ships: int, pos: Position, prod: int, radius: float):
        assert isinstance(pos, Position)
        assert isinstance(owner, User)

        self.n = n
        self.owner = owner
        self.ships = ships
        self.pos = pos
        self.prod = prod
        self.radius = radius

        self.dispatched_fleets = FleetGroup()
        self.incoming_fleets = FleetGroup()

    def distance_to(self, other):
        assert isinstance(other, Planet) or isinstance(other, Fleet)
        return sqrt((self.pos.x - other.pos.x) ** 2 + (self.pos.y - other.pos.y) ** 2)

    def __repr__(self):
        return 'planet[n:' + str(self.n) + ' ' + self.owner.name + " " + "ships:" + str(self.ships) + " " + "prod:" + str(self.prod) + " pos:" + str(self.pos) + "]"
    def send(self, ratio, target):
        assert isinstance(target, Planet)
        sys.stdout.write("/SEND %d %d %d\n" %(70, self.n, target.n) + "\n")
        sys.stdout.flush()

class Fleet():
    def __init__(self, n: int, xid: int, owner: User, ships: int, pos: Position, source: Planet, target: Planet, radius: int):
        self.n = n
        self.xid = xid
        self.owner = owner
        self.ships = ships
        self.pos = pos
        self.source = source
        self.target = target
        self.radius = radius

    def __repr__(self):
        return 'fleet[ships:' + str(self.ships) + ' o:' + self.owner.name + ']'
    pass

########################################################################################

def product(*args):
    return functools.reduce(lambda a, b: a * b, args)

########################################################################################

class GameManager():

    class InternalItem:
        def __init__(self,**args):
            self.n = 0
            self.__dict__ = args

    class InternalState:
        def __init__(self):
            self.reset()
        def reset(self):
            self.state = ''
            self.items = {}
            self.you = 0

    def __init__(self, botfunc):
        self.botfunc = botfunc
        g = self.InternalState()
        while True:
            try:
                line = sys.stdin.readline()
            except:
                break
            if not line:
                break
            line = line.rstrip()
            if len(line) == 0:
                continue
            self.parse(g,line)

    def create_galaxy(self, g):
        users = {}

        planet_bucket = []
        fleet_bucket = []

        for check_key, o in g.items.items():
            assert check_key == o.n
            if o.type == 'user':
                users[o.n] = User(n = o.n, xid = o.xid, name = o.name, color = o.color, team = o.team)
            elif o.type == 'planet':
                planet_bucket.append(o)
            elif o.type == 'fleet':
               fleet_bucket.append(o)
            else:
                raise Exception("uknown type of entity: " + o.type)

        planets = {}

        for o in planet_bucket:
            owner = users[o.owner]
            assert o.ships - round(o.ships) < 0.0001
            new_planet = Planet(n = o.n, owner = owner, ships = int(o.ships), pos = Position(o.x, o.y), prod = o.production, radius = o.radius)
            planets[o.n] = new_planet
            owner.planets.append(new_planet)

        fleets = FleetGroup()
        for o in fleet_bucket:
            owner = users[o.owner]
            source = planets[o.source]
            target = planets[o.target]
            pos = Position(o.x, o.y)
            new_fleet = Fleet(n = o.n, xid = o.xid, owner = owner, ships = o.ships, pos = pos, source = source, target = target, radius = o.radius)
            fleets.append(new_fleet)
            owner.fleets.append(new_fleet)

            source.dispatched_fleets.append(new_fleet)
            target.incoming_fleets.append(new_fleet)

        return Galaxy([v for k, v in users.items()], PlanetGroup([v for k, v in planets.items()]), fleets)

    def parse(self, g, line):
        t = line.split("\t")
        if t[0][0] != "/":
            nFields, fields = len(t[0]),t[0].upper()
            i = 1
            while i < len(t):
                n = int(t[i])
                i+= 1
                if n in g.items:
                    o = g.items[n]
                    for k in fields:
                        v = t[i]
                        i += 1
                        if k == 'X': o.x = float(v)
                        elif k == 'Y': o.y = float(v)
                        elif k == 'S': o.ships = float(v)
                        elif k == 'R': o.radius = float(v)
                        elif k == 'O': o.owner = float(v)
                        elif k == 'T': o.target = float(v)
                else:
                    i += nFields
            return
        if t[0] == "/TICK":
            self.botfunc(self.create_galaxy(g))
            sys.stdout.write("/TOCK" + "\n")
            sys.stdout.flush()
        elif t[0] == "/PRINT": print("\t".join(t[1:]))
        elif t[0] == "/RESULTS": print("\t".join(t[1:]))
        elif t[0] == "/RESET": g.reset()
        elif t[0] == "/SET":
            if t[1] == "YOU": g.you = int(t[2])
            elif t[1] == "STATE": g.state = t[2]
        elif t[0] == "/USER":
            o = self.InternalItem(n=int(t[1]), type="user", name=t[2], color=int(t[3],16), team=int(t[4]), xid=int(t[5]))
            g.items[o.n] = o
        elif t[0] == "/PLANET":
            o = self.InternalItem(n=int(t[1]), type="planet", owner=int(t[2]), ships=float(t[3]), x=float(t[4]), y=float(t[5]), production=float(t[6]), radius=float(t[7]))
            g.items[o.n] = o
        elif t[0] == "/FLEET":
            o = self.InternalItem(n=int(t[1]), type="fleet", owner=int(t[2]), ships=float(t[3]), x=float(t[4]), y=float(t[5]), source=int(t[6]), target=int(t[7]), radius=float(t[8]), xid=int(t[9]))
            g.items[o.n] = o
        elif t[0] == "/DESTROY":
            n = int(t[1])
            if n in g.items:
                del(g.items[n])
        elif t[0] == "/ERROR":
            print("\t".join(t[1:]))
        else:
            print("unhandled command: " + "\t".join(t))

def print(*args):
    sys.stderr.write(' '.join([str(x) for x in args]) + "\n")
    sys.stderr.flush()

if __name__ == "__main__":
    GameManager(bot)
