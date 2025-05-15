import time
from natnetpacket.NatNetClient import NatNetClient
import sys

# Configuration
TARGET_RB_NAME = "A"  # The name of the rigid body to track
SERVER_IP = "10.40.49.47"
CLIENT_IP = "127.0.0.1" # Or your client's IP address on the network

def receive_new_frame(data_dict):
    frame_number = data_dict.get("frame_number", "N/A")
    print(f"--- Frame: {frame_number} ---")
    mocap_data_obj = data_dict.get("mocap_data")
    if not mocap_data_obj:
        print("  Warning: No mocap_data in frame.")
        return

    # Check for rigid_body_data attribute within mocap_data
    if hasattr(mocap_data_obj, "rigid_body_data") and mocap_data_obj.rigid_body_data:
        rb_data_container = mocap_data_obj.rigid_body_data
        
        # Based on our diagnostic output, we now know the right attribute name
        if hasattr(rb_data_container, 'rigid_body_list') and rb_data_container.rigid_body_list:
            rigid_body_list = rb_data_container.rigid_body_list
            print(f"  Found {len(rigid_body_list)} rigid body/bodies in this frame:")
            
            for i, rb_item in enumerate(rigid_body_list):
                print(f"    --- Rigid Body #{i+1} ---")
                if hasattr(rb_item, '__dict__'):
                    for key, value in rb_item.__dict__.items():
                        processed_value = value
                        if isinstance(value, bytes): # Attempt to decode common byte string attributes
                            try:
                                processed_value = value.decode('utf-8').rstrip('\x00')
                            except UnicodeDecodeError:
                                processed_value = str(value) # Fallback if decode fails
                        print(f"      {key}: {processed_value}")
                else:
                    print(f"      Rigid body item data: {rb_item}") # Fallback if no __dict__
        else:
            print("  'rigid_body_data' found but has no rigid_body_list or it's empty.")
    else:
        print("  No 'rigid_body_data' attribute found in mocap_data or it's empty/None.")
    print("--- End of Frame Data ---")


if __name__ == "__main__":
    streaming_client = NatNetClient()

    streaming_client.set_client_address(CLIENT_IP)
    streaming_client.set_server_address(SERVER_IP)
    # streaming_client.set_use_multicast(False) # Uncomment if not using multicast

    print(f"Attempting to connect to NatNet server for Rigid Body Tracking:")
    print(f"  Client IP: {streaming_client.get_client_address()}")
    print(f"  Server IP: {streaming_client.get_server_address()}")
    print(f"  Tracking Rigid Body: '{TARGET_RB_NAME}'")
    if streaming_client.use_multicast:
        print(f"  Using Multicast: True (Default Address: {streaming_client.multicast_address})")
    else:
        print(f"  Using Multicast: False")


    streaming_client.new_frame_listener = receive_new_frame
    print("Starting NatNet client thread...")
    is_running_initially = streaming_client.run()

    if not is_running_initially:
        print("ERROR: Could not start NatNet client. Please check connection and IPs.")
        sys.exit(1)
    else:
        print(f"NatNet client running. Monitoring for Rigid Body '{TARGET_RB_NAME}'...")

    try:
        while True:
            time.sleep(1)  # Keep main thread alive
            # The actual data processing happens in the receive_new_frame callback
    except KeyboardInterrupt:
        print("Stopping NatNet client due to KeyboardInterrupt...")
    finally:
        print() 
        if is_running_initially:
            print("Shutting down NatNet client...")
            streaming_client.shutdown()
        else:
            print("NatNet client was not started, no shutdown needed.")
        print("NatNet client stopped.")

    print("Exiting script.") 