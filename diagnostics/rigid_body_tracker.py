#!/usr/bin/env python3
import time
import argparse
from optitrack_python.streaming.NatNetClient import NatNetClient
import sys
import datetime
import traceback

# Configuration
TARGET_RB_NAME = "A"  # The name of the rigid body to track


# Variables for tracking position changes
last_frame_data = None  # Will store (position, orientation) tuple
identical_frames_detected = False
identical_frames_count = 0
total_frames_received = 0

# Command-line arguments (will be set in main)
verbose_mode = True
show_frame_info = False
stats_interval = 1

# Add tracking for connection health
connection_dropped = False
last_frame_time = 0
max_frame_gap = 5  # seconds without frames before considering connection lost

# Global variables for tracking
last_position = None
identical_count_total = 0      # Total identical frames for the entire run
identical_count_interval = 0   # Identical frames in the current reporting interval
total_frames = 0

def receive_new_frame(data_dict):
    """Callback function that processes each frame from NatNet"""
    global last_position, identical_count_total, identical_count_interval, total_frames
    
    # Just count frames and get frame number
    total_frames += 1
    frame_number = data_dict.get('frame_number', 'N/A')
    
    # Extract mocap data, rigid body data, and the first rigid body's position
    mocap_data = data_dict.get('mocap_data')
    if not mocap_data or not hasattr(mocap_data, "rigid_body_data"):
        return
        
    rigid_body_data = mocap_data.rigid_body_data
    if not hasattr(rigid_body_data, 'rigid_body_list') or not rigid_body_data.rigid_body_list:
        return
        
    # Get the first rigid body
    try:
        rb = rigid_body_data.rigid_body_list[0]
        position = getattr(rb, 'pos', None)
        
        if not position:
            return
            
        # Check if position matches the previous frame
        if last_position is not None and position == last_position:
            identical_count_total += 1
            identical_count_interval += 1
            print(f"!!! IDENTICAL POSITION in frame {frame_number} !!!")
            
        # Store current position for next comparison
        last_position = position
        
        # Print details in verbose mode
        if verbose_mode and total_frames % 100 == 0:  # Only print every 100th frame
            print(f"Frame {frame_number} Position: {position}")
            
    except Exception as e:
        if verbose_mode:
            print(f"Error processing frame: {e}")

def check_connection_health(streaming_client):
    """Check if we're still receiving frames and try to reconnect if needed"""
    global connection_dropped, last_frame_time
    
    current_time = time.time()
    
    # If we haven't received a frame for a while, consider the connection dropped
    if last_frame_time > 0 and current_time - last_frame_time > max_frame_gap:
        if not connection_dropped:
            connection_dropped = True
            print(f"\nWARNING: No frames received for {max_frame_gap}+ seconds at {datetime.datetime.now().strftime('%H:%M:%S')}")
            print(f"Last frame count: {total_frames_received}")
            
            # Attempt to reconnect
            try:
                print("Attempting to reconnect...")
                streaming_client.shutdown()
                time.sleep(1)  # Wait briefly before restarting
                
                # Restart the client
                success = streaming_client.run()
                if success:
                    print("Reconnection successful.")
                else:
                    print("Reconnection failed.")
            except Exception as e:
                print(f"Error during reconnection attempt: {str(e)}")
                if verbose_mode:
                    traceback.print_exc()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple rigid body position tracker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    # Set verbosity
    verbose_mode = args.verbose
    
    # Create NatNet client
    client = NatNetClient()
    client.set_server_address("10.40.49.47")

    # Set up client
    print("Connecting to NatNet server...")
    client.new_frame_listener = receive_new_frame
    success = client.run()
    
    if not success:
        print("Error: Failed to start client")
        sys.exit(1)
    
    print("Client running. Press Ctrl+C to exit.")
    start_time = time.time()
    last_update = 0
    frames_previous = 0  # Track frames from previous interval
    
    try:
        while True:
            # Update status every second
            current_time = time.time()
            if current_time - last_update >= 1.0:
                run_time = current_time - start_time
                hours = int(run_time // 3600)
                minutes = int((run_time % 3600) // 60)
                seconds = int(run_time % 60)
                
                # Calculate frames in this interval
                frames_interval = total_frames - frames_previous
                frames_previous = total_frames
                
                # Print status
                status_line = f"Status: Frames={total_frames} (+{frames_interval}/s), "
                status_line += f"Identical: {identical_count_interval} (interval) / {identical_count_total} (total), "
                status_line += f"Runtime={hours:02d}:{minutes:02d}:{seconds:02d}"
                print(status_line)
                
                # Reset interval counters
                identical_count_interval = 0
                last_update = current_time
                
            time.sleep(0.5)  # Shorter sleep interval
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.shutdown()
        
        # Print summary
        print("\n=== SUMMARY ===")
        print(f"Total frames: {total_frames}")
        print(f"Total identical positions: {identical_count_total}")
        if total_frames > 0:
            print(f"Percentage identical: {(identical_count_total/total_frames)*100:.2f}%")
        print("===============")

    print("Exiting script.") 