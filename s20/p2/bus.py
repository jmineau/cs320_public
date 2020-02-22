from math import sin, cos, asin, sqrt, pi
from datetime import datetime
from zipfile import ZipFile
import copy
import pandas as pd


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
                    self.trip_id = trips.loc[row, 'trip_id']
                    self.route_id = trips.loc[row, 'route_short_name']
                    self.bikes_allowed = trips.loc[row, 'bikes_allowed']
                    trip = Trip(self.trip_id, self.route_id, self.bikes_allowed)
                    trip_list.add(trip)
        trip_list = list(trip_list)
        return sorted(trip_list, key = lambda x: x.trip_id)
    
    def get_stops(self):
        stop_list = set()
        trip_id_list=(o.trip_id for o in self.get_trips())
        trip_id_list=list(set(trip_id_list))
        with ZipFile('mmt_gtfs.zip') as zf:
            with zf.open('stop_times.txt') as f:
                with zf.open('stops.txt') as g:
                    self.stop_times = pd.read_csv(f, parse_dates = ['arrival_time','departure_time'], keep_date_col=True)
                    self.stops = pd.read_csv(g)
                    stops = self.stops
                    times = self.stop_times
                    times = times[times['trip_id'].isin(trip_id_list)]
                    times = times.drop_duplicates(subset='stop_id').set_index('stop_id')
                    for stop_id in times.index:
                        self.stop_id = stop_id
                        single_stop=stops[stops['stop_id']==self.stop_id]
                        latlon = (float(single_stop['stop_lat']), float(single_stop['stop_lon']))
                        self.location = Location(latlon = latlon)
                        self.wheelchair_boarding = int(single_stop['wheelchair_boarding'])
                        stop = Stop(self.stop_id, self.location, self.wheelchair_boarding)
                        stop_list.add(stop)
        stop_list = list(stop_list)
        return sorted(stop_list, key = lambda x: x.stop_id)
    
    def get_stops_rect(self, xlim, ylim):
        stop_list = self.get_stops()
        rect_stop_list = []
        x1,x2 = xlim[0],xlim[1]
        y1,y2 = ylim[0],ylim[1]
        if x1 > x2:
            x1,x2 = x2,x1
        if y1 > y2:
            y1,y2 = y2,y1
        for stop in stop_list:
            if stop.location.x >= x1 and stop.location.x <= x2 and stop.location.y >= y1 and stop.location.y <= y2:
                rect_stop_list.append(stop)
        return rect_stop_list
        
        

                                                    
                
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
