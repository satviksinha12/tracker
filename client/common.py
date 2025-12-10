import requests
import math

API_BASE = "https://v2svirtualalliance.web.app/api"  # Live Production URL

class FlightPhase:
    BOARDING = "Boarding"
    TAXI_OUT = "Taxi Out"
    TAKEOFF = "Takeoff"
    CLIMBING = "Climbing"
    CRUISE = "Cruise"
    DESCENDING = "Descending"
    APPROACH = "Approach"
    LANDING = "Landing"
    TAXI_IN = "Taxi In"
    PARKED = "Parked"

class FlightManager:
    def __init__(self, pilot_id, callsign, aircraft_type, dep, arr):
        self.pilot_id = pilot_id
        self.callsign = callsign
        self.aircraft_type = aircraft_type
        self.dep = dep
        self.arr = arr
        self.phase = FlightPhase.BOARDING
        self.flight_id = f"{callsign}"
        
        self.max_alt = 0
        self.distance_flown = 0
        self.last_lat = None
        self.last_lon = None
        self.landing_rate = 0
        self.fuel_used = 0
        self.initial_fuel = None

    def update_phase(self, alt, speed, on_ground, vertical_speed, engines_running):
        # Basic state machine
        if self.phase == FlightPhase.BOARDING:
            if engines_running and speed > 5:
                self.phase = FlightPhase.TAXI_OUT
        
        elif self.phase == FlightPhase.TAXI_OUT:
            if not on_ground and alt > 100: # Slightly airborne
                self.phase = FlightPhase.TAKEOFF
            elif speed > 40 and on_ground:
                self.phase = FlightPhase.TAKEOFF

        elif self.phase == FlightPhase.TAKEOFF:
            if alt > 1000 and vertical_speed > 100:
                self.phase = FlightPhase.CLIMBING
        
        elif self.phase == FlightPhase.CLIMBING:
            if vertical_speed < 100 and vertical_speed > -100 and alt > 10000:
                self.phase = FlightPhase.CRUISE
        
        elif self.phase == FlightPhase.CRUISE:
            if vertical_speed < -500:
                self.phase = FlightPhase.DESCENDING
        
        elif self.phase == FlightPhase.DESCENDING:
            if alt < 3000:
                self.phase = FlightPhase.APPROACH

        elif self.phase == FlightPhase.APPROACH:
            if on_ground:
                self.phase = FlightPhase.LANDING
        
        elif self.phase == FlightPhase.LANDING:
            if speed < 30:
                self.phase = FlightPhase.TAXI_IN
        
        elif self.phase == FlightPhase.TAXI_IN:
            if not engines_running and speed < 1:
                self.phase = FlightPhase.PARKED

        if alt > self.max_alt:
            self.max_alt = alt

        return self.phase

    def calculate_distance(self, lat, lon):
        if self.last_lat is not None:
            # Haversine distance for small increments
            R = 6371  # km
            dLat = math.radians(lat - self.last_lat)
            dLon = math.radians(lon - self.last_lon)
            a = math.sin(dLat/2) * math.sin(dLat/2) + \
                math.cos(math.radians(self.last_lat)) * math.cos(math.radians(lat)) * \
                math.sin(dLon/2) * math.sin(dLon/2)
            c = 2 * math.asin(math.sqrt(a))
            dist = R * c
            self.distance_flown += dist
        
        self.last_lat = lat
        self.last_lon = lon

    def send_acars(self, lat, lon, alt, heading, speed):
        payload = {
            "pilotId": self.pilot_id,
            "flightId": self.flight_id,
            "callsign": self.callsign,
            "dep": self.dep,
            "arr": self.arr,
            "aircraft": self.aircraft_type,
            "lat": lat,
            "lon": lon,
            "alt": int(alt),
            "heading": int(heading),
            "speed": int(speed),
            "phase": self.phase
        }
        try:
            requests.post(f"{API_BASE}/acars", json=payload, timeout=2)
        except:
            pass # Ignore connection blips for ACARS

    def submit_pirep(self, landing_rate, fuel_used, total_time_min):
        payload = {
            "flightNumber": self.flight_id,
            "dep": self.dep,
            "arr": self.arr,
            "aircraft": self.aircraft_type,
            "flightTime": f"{int(total_time_min // 60)}:{int(total_time_min % 60):02d}",
            "distance": int(self.distance_flown * 0.539957), # KM to NM
            "landingRate": int(landing_rate),
            "fuelUsed": int(fuel_used),
            "status": "Accepted" # Auto-accept for now, or "Pending"
        }
        try:
            print(f"Submitting PIREP: {payload}")
            # Note: This endpoint might need Auth. For now, assuming open or using a simple secret if we added one. 
            # In production, we'd add an API Key header here.
            res = requests.post(f"{API_BASE}/pireps", json=payload)
            if res.status_code == 200:
                print("PIREP Submitted Successfully!")
                return True
            else:
                print(f"PIREP Submission Failed: {res.text}")
                return False
        except Exception as e:
            print(f"Error submitting PIREP: {e}")
            return False
