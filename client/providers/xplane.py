import socket
import struct
import time
from common import FlightManager, FlightPhase

def run_xplane(pilot_id, flight_id, aircraft, dep, arr, cruise_alt):
    # UDP Setup
    UDP_IP = "0.0.0.0"
    UDP_PORT = 49000
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    print(f"Listening for X-Plane on port {UDP_PORT}...")
    print("Please ensure Data Output for indexes 3, 17, 20 are checked in X-Plane Settings.")

    manager = FlightManager(pilot_id, flight_id, aircraft, dep, arr, cruise_alt)
    start_time = time.time()

    data_store = {
        "lat": 0, "lon": 0, "alt": 0,
        "heading": 0, "speed": 0, "vs": 0,
        "on_ground": False, "engines_running": True # Simplified
    }

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            
            # X-Plane sends 5 bytes header "DATA<" then sets of 36 bytes (4 byte index + 8 floats)
            # We skip first 5 bytes
            header = data[0:5]
            if header != b'DATA<':
                continue

            # Read blocks
            num_values = (len(data) - 5) // 36
            
            for i in range(num_values):
                offset = 5 + i * 36
                idx = struct.unpack('<i', data[offset:offset+4])[0]
                values = struct.unpack('<8f', data[offset+4:offset+36])

                if idx == 3: # Speed (Indicated, Mach, True, Gs)
                    data_store["speed"] = values[3] * 1.94384 # m/s to knots
                
                elif idx == 17: # Pitch, Roll, Hdg
                    data_store["heading"] = values[2]
                
                elif idx == 20: # Lat, Lon, Alt
                    data_store["lat"] = values[0]
                    data_store["lon"] = values[1]
                    data_store["alt"] = values[2]

            # Derived Data (Simple estimation)
            # VS can be derived from alt change or requested from another dataref, simplified here
            
            # On Ground check (simple alt check or speed check for now)
            # X-Plane actually has a gear force dataref but index 20 doesn't have it.
            # Using Speed < 30 and Alt < Dep Elevation + 50 as proxy or just rely on state machine logic
            data_store["on_ground"] = data_store["alt"] < 500 and data_store["speed"] < 40 

            current_phase = manager.update_phase(
                alt=data_store["alt"], 
                speed=data_store["speed"], 
                on_ground=data_store["on_ground"], 
                vertical_speed=0, # Need index 4 for VS, assuming cruise for now if not tracked
                engines_running=True # Hard to track engine state via simple UDP without index 37
            )

            manager.calculate_distance(data_store["lat"], data_store["lon"])
            manager.send_acars(
                data_store["lat"], data_store["lon"], 
                data_store["alt"], data_store["heading"], 
                data_store["speed"]
            )
            
            # Only print every 1s
            if int(time.time()) % 2 == 0:
                 print(f"\rPhase: {current_phase} | Alt: {int(data_store['alt'])} | GS: {int(data_store['speed'])}", end="")

            if current_phase == FlightPhase.PARKED:
                print("\nFlight Parked. Submitting PIREP...")
                duration = (time.time() - start_time) / 60
                manager.submit_pirep(-100, 0, duration)
                break
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
