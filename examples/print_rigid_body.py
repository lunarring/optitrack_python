#!/usr/bin/env python3
import time
import argparse
from optitrack_python.NatNetClient import NatNetClient
import sys


def receive_new_frame(data_dict):
    """Callback function that processes each frame from NatNet"""
    global target_rb_name, verbose_mode
    
    # Get frame number
    frame_number = data_dict.get('frame_number', 'N/A')
    
    # Extract mocap data
    mocap_data = data_dict.get('mocap_data')
    if not mocap_data or not hasattr(mocap_data, "rigid_body_data"):
        if verbose_mode:
            print(f"[Frame {frame_number}] No mocap_data received.")
        return
        
    rigid_body_data = mocap_data.rigid_body_data
    if (not hasattr(rigid_body_data, 'rigid_body_list') or 
            not rigid_body_data.rigid_body_list):
        if verbose_mode:
            print(f"[Frame {frame_number}] No rigid_body_list found.")
        return
    
    # Look for the target rigid body - using sz_name as used in track_rigid_body_A.py
    found = False
    for rb in rigid_body_data.rigid_body_list:
        # Check if rb has attribute sz_name
        rb_name = getattr(rb, 'sz_name', None)
        
        if rb_name == target_rb_name:
            pos = getattr(rb, 'pos', None)
            if pos is not None:
                print(f"[Frame {frame_number}] Rigid Body '{rb_name}' "
                      f"Position: {pos}")
            else:
                if verbose_mode:
                    print(f"[Frame {frame_number}] Rigid Body '{rb_name}' "
                          f"has no position data.")
            found = True
            break
            
    if not found and verbose_mode:
        print(f"[Frame {frame_number}] Rigid Body '{target_rb_name}' "
              f"not found in this frame.")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Print rigid body position")
    parser.add_argument(
        "-n", "--name", default="A", 
        help="Name of the rigid body to track (default: 'A')"
    )
    parser.add_argument(
        "-s", "--server", default="10.40.49.47",
        help="IP address of the NatNet server"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    args = parser.parse_args()
    
    # Set global variables
    target_rb_name = args.name
    verbose_mode = args.verbose
    
    # Create NatNet client
    client = NatNetClient()
    client.set_server_address(args.server)

    # Set up client
    print(f"Connecting to NatNet server at {args.server}...")
    print(f"Tracking rigid body: '{target_rb_name}'")
    client.new_frame_listener = receive_new_frame
    success = client.run()
    
    if not success:
        print("Error: Failed to start client")
        sys.exit(1)
    
    print("Client running. Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(0.1)  # Small sleep to prevent high CPU usage
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.shutdown()
        print("Exiting script.")