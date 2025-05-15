import time
import argparse
from natnetpacket.NatNetClient import NatNetClient
import sys
import datetime
import traceback

# Configuration
TARGET_RB_NAME = "A"  # The name of the rigid body to track
SERVER_IP = "10.40.49.47"
CLIENT_IP = "127.0.0.1" # Or your client's IP address on the network

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

def receive_new_frame(data_dict):
    global last_frame_data, identical_frames_detected, identical_frames_count, total_frames_received, last_frame_time, connection_dropped
    
    # Update the timestamp for last received frame
    last_frame_time = time.time()
    
    # Reset connection dropped flag if we're receiving frames again
    if connection_dropped:
        connection_dropped = False
        print(f"INFO: Connection resumed at {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    frame_number = data_dict.get('frame_number')
    if frame_number is None:
        if verbose_mode:
            print("Warning: Frame number not found in data_dict.")
        return

    total_frames_received += 1

    # Look for rigid body data
    mocap_data = data_dict.get('mocap_data')
    if not mocap_data or not hasattr(mocap_data, "rigid_body_data"):
        return

    rb_data = mocap_data.rigid_body_data
    if not hasattr(rb_data, 'rigid_body_list') or not rb_data.rigid_body_list:
        if verbose_mode:
            print(f"No rigid bodies found in frame {frame_number}")
        return

    # Get the first rigid body (assuming it's the one we want to track)
    rb = rb_data.rigid_body_list[0]
    
    # Extract position and orientation
    position = getattr(rb, 'pos', None)
    
    # Look for quaternion components
    qx = getattr(rb, 'qx', None)
    qy = getattr(rb, 'qy', None)
    qz = getattr(rb, 'qz', None)
    qw = getattr(rb, 'qw', None)
    
    if all(x is not None for x in [qx, qy, qz, qw]):
        orientation = (qx, qy, qz, qw)
    else:
        # Try alternate ways of getting orientation
        orientation = getattr(rb, 'rot', None)
    
    # If we couldn't get position or orientation, skip this frame
    if position is None or orientation is None:
        if verbose_mode:
            print(f"Missing position or orientation data in frame {frame_number}")
        return
    
    # Combine position and orientation for comparison
    current_frame_data = (position, orientation)
    
    # Check for identical frames (which might indicate dropped frames)
    if last_frame_data is not None and current_frame_data == last_frame_data:
        if not identical_frames_detected:
            identical_frames_detected = True
        identical_frames_count += 1
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"WARNING: Identical rigid body data detected in frame {frame_number}")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    # Update for next comparison
    last_frame_data = current_frame_data
    
    # Print raw data in verbose mode
    if verbose_mode:
        print(f"--- Frame {frame_number} Rigid Body Data ---")
        print(f"  Position: {position}")
        print(f"  Orientation: {orientation}")
        # Print all attributes of the rigid body
        print(f"  All attributes:")
        if hasattr(rb, '__dict__'):
            for key, value in rb.__dict__.items():
                processed_value = value
                if isinstance(value, bytes):
                    try:
                        processed_value = value.decode('utf-8').rstrip('\x00')
                    except:
                        processed_value = str(value)
                print(f"    {key}: {processed_value}")
        print("--- End of Frame Data ---")

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
    parser = argparse.ArgumentParser(description="Monitor rigid body data for identical frames (potential drops)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed frame data")
    parser.add_argument("--interval", "-i", type=int, default=1, 
                        help="Interval in seconds for printing status updates (default: 1)")
    args = parser.parse_args()

    verbose_mode = args.verbose
    status_update_interval = args.interval

    streaming_client = NatNetClient()
    monitoring_active_start_time = 0

    # Network configuration
    client_ip = "127.0.0.1"
    server_ip = "10.40.49.47"  # Motive server IP

    streaming_client.set_client_address(client_ip)
    streaming_client.set_server_address(server_ip)
    # streaming_client.set_use_multicast(False)  # Uncomment if not using multicast

    print(f"Attempting to connect to NatNet server:")
    print(f"  Client IP: {streaming_client.get_client_address()}")
    print(f"  Server IP: {streaming_client.get_server_address()}")
    print(f"  Using Multicast: {streaming_client.use_multicast}")
    if streaming_client.use_multicast:
        print(f"  Multicast Address: {streaming_client.multicast_address}")
    print(f"  Verbose mode: {'ON' if verbose_mode else 'OFF'}")

    streaming_client.new_frame_listener = receive_new_frame
    print("Starting NatNet client thread...")
    is_running = streaming_client.run()

    if not is_running:
        print("ERROR: Could not start NatNet client. Please check connection and IPs.")
    else:
        monitoring_active_start_time = time.time()
        print(f"NatNet client running. Monitoring rigid body data for identical frames...")

    try:
        if is_running:
            last_status_print_time = 0
            while True:  # Loop indefinitely
                current_time = time.time()
                if monitoring_active_start_time > 0 and (current_time - last_status_print_time >= status_update_interval or last_status_print_time == 0):
                    elapsed_seconds = current_time - monitoring_active_start_time
                    hours = int(elapsed_seconds // 3600)
                    minutes = int((elapsed_seconds % 3600) // 60)
                    seconds = int(elapsed_seconds % 60)
                    formatted_elapsed_time = f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"

                    status_str = "IDENTICAL FRAMES DETECTED!" if identical_frames_detected else "OK"
                    
                    status_line = f"Status: {status_str} | Frames: {total_frames_received} | Identical: {identical_frames_count} | Elapsed: {formatted_elapsed_time}"
                    if total_frames_received > 0:
                        pct = (identical_frames_count / total_frames_received) * 100
                        status_line += f" | Identical %: {pct:.2f}%"
                    
                    print(status_line)
                    last_status_print_time = current_time
                
                time.sleep(1)  # Keep main thread alive
        
    except KeyboardInterrupt:
        print("\nStopping NatNet client due to KeyboardInterrupt...")
    finally:
        print()  # Ensure cursor moves to next line before final summary
        if is_running:
            print("Shutting down NatNet client...")
            streaming_client.shutdown()
        
        print("NatNet client stopped.")
        print("\n=== FINAL STATISTICS ===")
        print(f"Total frames processed: {total_frames_received}")
        print(f"Identical frames detected: {identical_frames_count}")
        if total_frames_received > 0:
            pct = (identical_frames_count / total_frames_received) * 100
            print(f"Percentage of identical frames: {pct:.2f}%")
        
        if identical_frames_detected:
            print("Summary: Identical frames WERE detected during this session.")
        else:
            print("Summary: No identical frames detected during this session.")
        print("========================")

    print("Exiting script.") 