from math import sin, cos, asin, sqrt, pi
from datetime import datetime
from zipfile import ZipFile
import copy
import pandas as pd
from graphviz import Digraph, Graph


def haversine_miles(lat1, lon1, lat2, lon2):
    """Calculates the distance between two points on earth using the
    harversine distance (distance between points on a sphere)
    See: https://en.wikipedia.org/wiki/Haversine_formula

    :param lat1: latitude of point 1
    :param lon1: longitude of point 1
    :param lat2: latitude of point 2
    :param lon2: longitude of point 2
    :return: distance in miles between points
    """
    lat1, lon1, lat2, lon2 = (a/180*pi for a in [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon/2) ** 2
    c = 2 * asin(min(1, sqrt(a)))
    d = 3956 * c
    return d


class Location:
    """Location class to convert lat/lon pairs to
    flat earth projection centered around capitol
    """
    capital_lat = 43.074683
    capital_lon = -89.384261

    def __init__(self, latlon=None, xy=None):
        if xy is not None:
            self.x, self.y = xy
        else:
            # If no latitude/longitude pair is given, use the capitol's
            if latlon is None:
                latlon = (Location.capital_lat, Location.capital_lon)

            # Calculate the x and y distance from the capital
            self.x = haversine_miles(Location.capital_lat, Location.capital_lon,
                                     Location.capital_lat, latlon[1])
            self.y = haversine_miles(Location.capital_lat, Location.capital_lon,
                                     latlon[0], Location.capital_lon)

            # Flip the sign of the x/y coordinates based on location
            if latlon[1] < Location.capital_lon:
                self.x *= -1

            if latlon[0] < Location.capital_lat:
                self.y *= -1

    def dist(self, other):
        """Calculate straight line distance between self and other"""
        return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __repr__(self):
        return "Location(xy=(%0.2f, %0.2f))" % (self.x, self.y)


class Node:
    def __init__(self, stops, i=1):
        if i != 6:
            if i % 2 != 0:
                stops = sorted(stops, key = lambda s: s.location.x)
            else:
                stops = sorted(stops, key = lambda s: s.location.y)
            left_stops = stops[:len(stops)//2]
            right_stops = stops[len(stops)//2:]
            i += 1
            self.val = stops[len(stops)//2].location
            self.left = Node(left_stops, i)
            self.right = Node(right_stops, i)
        else:
            self.val = stops
            self.left = None
            self.right = None
        return
    
    def to_graphviz(self, g=None):
        if g == None:
            g = Digraph()
            
        # draw self
        g.node(repr(self.val))
    
        for label, child in [("L", self.left), ("R", self.right)]:
            if child != None:
                # draw child, recursively
                child.to_graphviz(g)
                
                # draw edge from self to child
                g.edge(repr(self.val), repr(child.val), label=label)
        return g
    
    def _repr_svg_(self):
        return self.to_graphviz()._repr_svg_()
    
    def search(self, xlim, ylim, found_stops=[], i=1):
        x1,x2 = xlim[0],xlim[1]
        y1,y2 = ylim[0],ylim[1]
        if x1 > x2:
            x1,x2 = x2,x1
        if y1 > y2:
            y1,y2 = y2,y1
        if i != 6:  
            if i % 2 != 0:
                i += 1
                if self.val.x >= x1 and self.val.x <= x2:
                    self.left.search(xlim, ylim, found_stops, i)
                    self.right.search(xlim, ylim, found_stops, i)
                elif self.val.x <= x1:
                    self.right.search(xlim, ylim, found_stops, i)
                else:
                    self.left.search(xlim, ylim, found_stops, i)
            else:
                i += 1
                if self.val.y >= y1 and self.val.y <= y2:
                    self.left.search(xlim, ylim, found_stops, i)
                    self.right.search(xlim, ylim, found_stops, i)
                elif self.val.y <= y1:
                    self.right.search(xlim, ylim, found_stops, i)
                else:
                    self.left.search(xlim, ylim, found_stops, i)
        else:
            for stop in self.val:
                if stop.location.x >= x1 and stop.location.x <= x2 and stop.location.y >= y1 and stop.location.y <= y2:
                    found_stops.append(stop)
        return found_stops

class BusDay:
    def __init__(self,time):        
        self.service_ids=None
        service_list=[]
        self.weekday=time.strftime('%A').lower()         
        with ZipFile('mmt_gtfs.zip') as zf:          
            with zf.open("calendar.txt") as f:
                self.calendar = pd.read_csv(f, parse_dates=['start_date','end_date'], keep_date_col=True)
                calendar=copy.deepcopy(self.calendar)
                calendar=calendar[((time<=calendar['end_date']) & (time>=calendar['start_date']))]
                calendar=calendar[calendar[self.weekday]==1]
                service_list.extend(list(calendar['service_id']))
                self.service_ids=sorted(service_list)
        self.trip_l = self.get_trips()
        self.stop_l = self.get_stops()
        return
    
    def get_trips(self, route_num: int = None):
        trip_list = set()
        with ZipFile('mmt_gtfs.zip') as zf:
            with zf.open('trips.txt') as f:
                self.trips = pd.read_csv(f)
                trips = self.trips
                #Finds trips for that day
                trips = trips[trips['service_id'].isin(self.service_ids)]
                if route_num != None:                  
                    #Finds trips of that route id
                    trips = (trips[((trips['route_id'])==int(route_num)) | (trips['route_short_name']==int(route_num))])
                for row in trips.index:
                    trip_id = trips.loc[row, 'trip_id']
                    route_id = trips.loc[row, 'route_short_name']
                    bikes_allowed = trips.loc[row, 'bikes_allowed']
                    trip = Trip(trip_id, route_id, bikes_allowed)
                    trip_list.add(trip)
        trip_list = list(trip_list)
        return sorted(trip_list, key = lambda x: x.trip_id)
            
    def get_stops(self):
        stop_list = set()
        trip_id_list=[]
        for trip in self.trip_l:
            trip_id_list.append(trip.trip_id)
        trip_id_list=list(set(trip_id_list))
        with ZipFile('mmt_gtfs.zip') as zf:
            with zf.open('stop_times.txt') as g:
                with zf.open('stops.txt') as h:
                    self.stop_times = pd.read_csv(g)
                    self.stops = pd.read_csv(h)
                    stops = self.stops
                    stops = stops.set_index('stop_id')
                    times = self.stop_times
                    #removes trips not in get_trips
                    times = times.loc[times['trip_id'].isin(trip_id_list),:]
                    #drops duplicate stops and sets the index of times to stop_id
                    times = times.drop_duplicates(subset='stop_id').set_index('stop_id')
                    #only uses stops in the stops file that are from set day
                    stops=stops.loc[stops.index.isin(times.index),:]
                    for stop_id in stops.index:
                        latlon = (float(stops.loc[stop_id,'stop_lat']), float(stops.loc[stop_id,'stop_lon']))
                        location = Location(latlon = latlon)
                        wheelchair_boarding = int(stops.loc[stop_id, 'wheelchair_boarding'])
                        stop = Stop(stop_id, location, wheelchair_boarding)
                        stop_list.add(stop)
        stop_list = list(stop_list)
        return sorted(stop_list, key = lambda x: x.stop_id)
    
    def get_stops_rect(self, xlim, ylim):      
        return Node(self.stop_l).search(xlim, ylim)
    
    def get_stops_circ(self, origin, radius):
        circ_list = []
        x = origin[0]
        y = origin[1]
        xlim = ((x-radius),(x+radius))
        ylim = ((y-radius),(y+radius))
        rect_stops = self.get_stops_rect(xlim, ylim)
        for stop in rect_stops:
            if stop.location.x**2 + stop.location.y**2 <= radius**2:
                circ_list.append(stop)
        return circ_list
    
class Trip:
    def __init__(self, trip_id, route_id, bikes_allowed):
        self.trip_id = trip_id
        self.route_id = route_id
        self.bikes_allowed = bool(bikes_allowed)        
        return
    
    def __repr__(self):
        return "Trip({}, {}, {})".format(self.trip_id,self.route_id,self.bikes_allowed)

class Stop:
    def __init__(self, stop_id, location, wheelchair_boarding):
        self.stop_id = stop_id
        self.location = location
        self.wheelchair_boarding = bool(wheelchair_boarding)
        return
    def __repr__(self):
        return "Stop({}, {}, {})".format(self.stop_id, self.location, self.wheelchair_boarding)