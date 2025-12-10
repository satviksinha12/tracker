import time
try:
    from SimConnect import SimConnect, AircraftRequests
except ImportError:
    SimConnect = None

from common import FlightManager, FlightPhase

def run_msfs(pilot_id, flight_id, aircraft, dep, arr, cruise_alt):
    if not SimConnect:
        print("Error: SimConnect library not installed. Please run 'pip install SimConnect'")
        return

    print("Connecting to MSFS...")
    try:
        sm = SimConnect()
        aq = AircraftRequests(sm, _time=2000)
    except Exception as e:
        print(f"Could not connect to MSFS: {e}")
        return

    manager = FlightManager(pilot_id, flight_id, aircraft, dep, arr, cruise_alt)
    
    print(f"Connected to MSFS! Tracking Flight {flight_id}")
    
    start_time = time.time()
    
    while True:
        try:
            lat = aq.get("PLANE_LATITUDE")
            lon = aq.get("PLANE_LONGITUDE")
            alt = aq.get("PLANE_ALTITUDE")
            hdg = aq.get("PLANE_HEADING_DEGREES_TRUE")
            spd = aq.get("AIRSPEED_TRUE")
            vs = aq.get("VERTICAL_SPEED")
            og = aq.get("SIM_ON_GROUND")
            
            # Engine running? (General 1)
            eng = aq.get("GENERAL_ENG_COMBUSTION:1")
            
            # Fuel
            fuel = aq.get("FUEL_TOTAL_QUANTITY")

            if lat is None or lon is None:
                time.sleep(1)
                continue

            current_phase = manager.update_phase(
                alt=alt, 
                speed=spd, 
                on_ground=bool(og), 
                vertical_speed=vs, 
                engines_running=bool(eng)
            )
            
            manager.calculate_distance(lat, lon)
            manager.send_acars(lat, lon, alt, hdg, spd)

            print(f"Phase: {current_phase} | Alt: {int(alt)} | GS: {int(spd)}")

            if current_phase == FlightPhase.PARKED:
                print("Flight Parked. Submitting PIREP...")
                duration_min = (time.time() - start_time) / 60
                
                # Mock landing rate/fuel for now as simple SimConnect wrapper might need more complex request for touch down rate
                landing_rate = -150 
                fuel_used = 0 
                
                if manager.submit_pirep(landing_rate, fuel_used, duration_min):
                    break
                else:
                    print("Retrying submission...")
                    time.sleep(5)

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n[MANUAL OVERRIDE] Tracking Paused.")
            choice = input("Do you want to file this PIREP now? (y/n): ").strip().lower()
            if choice == 'y':
                duration_min = (time.time() - start_time) / 60
                # Use last known vs or default
                l_rate = int(vs) if 'vs' in locals() else -150
                manager.submit_pirep(l_rate, 0, duration_min)
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
