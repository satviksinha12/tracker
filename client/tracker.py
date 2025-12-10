import sys
import os

# Add providers to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'providers'))

def main():
    print("========================================")
    print("      V2S Alliance ACARS Client     ")
    print("========================================")
    
    print("Select Simulator:")
    print("1. Microsoft Flight Simulator (2020/2024)")
    print("2. X-Plane 11/12 (UDP Mode)")
    
    choice = input("Enter choice (1/2): ").strip()
    
    print("\n--- Flight Details ---")
    pilot_id = input("Pilot ID (e.g., VA123): ").strip()
    callsign = input("Callsign (e.g., VA101): ").strip()
    aircraft = input("Aircraft (e.g., A320): ").strip()
    dep = input("Departure ICAO: ").strip().upper()
    arr = input("Arrival ICAO: ").strip().upper()
    
    if choice == "1":
        try:
            from providers.msfs import run_msfs
            run_msfs(pilot_id, callsign, aircraft, dep, arr)
        except ImportError:
            print("Error: Could not import MSFS provider. Are requirements installed?")
    elif choice == "2":
        try:
            from providers.xplane import run_xplane
            run_xplane(pilot_id, callsign, aircraft, dep, arr)
        except ImportError:
            print("Error: Could not import X-Plane provider.")
    else:
        print("Invalid selection.")

if __name__ == "__main__":
    main()
