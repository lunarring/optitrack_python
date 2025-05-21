#!/usr/bin/env python3
import time
import argparse
from optitrack_python.NatNetClient import NatNetClient
import sys
import copy


# Global variables for tracking
last_position = None
total_frames = 0
frame_positions = []  # Store recent positions for debugging
max_stored_positions = 5


def receive_new_frame(data_dict):
    """Callback function that processes each frame from NatNet"""
    global total_frames, last_position, frame_positions, raw_data_mode
    
    # Count frames
    total_frames += 1
    frame_number = data_dict.get('frame_number', 'N/A')
    
    # Extract mocap data
    mocap_data = data_dict.get('mocap_data')
    if not mocap_data or not hasattr(mocap_data, "rigid_body_data"):
        return
        
    rigid_body_data = mocap_data.rigid_body_data
    if not hasattr(rigid_body_data, 'rigid_body_list'):
        return
        
    if not rigid_body_data.rigid_body_list:
        return
    
    # Raw data mode - print the entire data structure for debugging
    if raw_data_mode and total_frames % 100 == 0:
        print("\nDEBUG - Raw rigid body data:")
        for i, rb in enumerate(rigid_body_data.rigid_body_list):
            print(f"  Body {i}:")
            # Print all attributes of the rigid body
            for attr in dir(rb):
                if not attr.startswith('__'):
                    try:
                        value = getattr(rb, attr)
                        print(f"    {attr}: {value}")
                    except Exception as e:
                        print(f"    {attr}: Error: {e}")
        print()

    # Process all rigid bodies
    found_target = False
    for i, rb in enumerate(rigid_body_data.rigid_body_list):
        # Get ID and name if available
        rb_id = getattr(rb, 'id_num', f"Unknown-{i}")
        rb_name = None
        
        # Try different possible attribute names for the rigid body name
        for name_attr in ['sz_name', 'name', 'rb_name', 'label']:
            if hasattr(rb, name_attr):
                rb_name = getattr(rb, name_attr)
                if rb_name:
                    break
                    
        if not rb_name:
            rb_name = f"ID_{rb_id}"
            
        # Try to get position data
        position = None
        for pos_attr in ['pos', 'position', 'xyz', 'loc']:
            if hasattr(rb, pos_attr):
                position = getattr(rb, pos_attr)
                if position:
                    break
        
        # Skip if no position data
        if not position:
            continue
            
        # Check if this is the target rigid body or the first one if no target specified
        if rb_name == target_rb_name or (not found_target and i == 0):
            found_target = True
            
            # Convert position to a tuple if it's not already
            if not isinstance(position, tuple):
                try:
                    position = tuple(position)
                except:
                    # If conversion fails, use string representation
                    position = str(position)
            
            # Store this position for debugging
            frame_positions.append((frame_number, rb_name, position))
            if len(frame_positions) > max_stored_positions:
                frame_positions.pop(0)
            
            # Check if position has changed
            position_changed = (last_position != position)
            
            # If position changed or it's time for a periodic update
            if position_changed or total_frames % 30 == 0:
                change_marker = "CHANGED ✓" if position_changed else "SAME ✗"
                print(f"Frame {frame_number}: {rb_name} - {change_marker}")
                print(f"  Position: {position}")
                
                if last_position and position_changed:
                    # Calculate difference from last position
                    try:
                        dx = position[0] - last_position[0]
                        dy = position[1] - last_position[1]
                        dz = position[2] - last_position[2]
                        print(f"  Delta: ({dx:.6f}, {dy:.6f}, {dz:.6f})")
                    except:
                        print(f"  Delta: Could not calculate")
                
                print()
            
            # Update last position
            last_position = position
            break


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
        "-r", "--raw", action="store_true",
        help="Print raw data mode (shows all rigid body attributes)"
    )
    args = parser.parse_args()
    
    # Set global variables
    target_rb_name = args.name
    raw_data_mode = args.raw
    
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
    print("Position will be printed when it changes.")
    print(f"Using raw data mode: {raw_data_mode}")
    
    try:
        # Keep the program running until keyboard interrupt
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        
        # Print the last few positions for debugging
        if frame_positions:
            print("\nLast recorded positions:")
            for i, (frame, name, pos) in enumerate(frame_positions):
                print(f"{i+1}. Frame {frame}: {name} - {pos}")
        
    finally:
        client.shutdown()
        print("Exiting script.")