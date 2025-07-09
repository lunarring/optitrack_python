import lunar_tools as lt
import time
import sys
import os
import argparse

# Add the parent directory to the path to import optitrack_python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optitrack_python.motive_receiver import MotiveReceiver
from optitrack_python.rigid_body import RigidBody

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send OptiTrack rigid body data via OSC')
    parser.add_argument('--osc-ip', required=True, help='OSC receiver IP address')
    parser.add_argument('--rigid-body', default='B', help='Rigid body name (default: B)')
    parser.add_argument('--rate', type=float, default=100.0, help='Sampling rate in Hz (default: 100)')
    args = parser.parse_args()
    
    # Configuration
    rigid_body_name = args.rigid_body
    sleep_time = 1.0 / args.rate  # Convert Hz to sleep time in seconds
    
    # Setup OptiTrack connection
    print("Connecting to OptiTrack...")
    motive = MotiveReceiver(server_ip="10.40.49.47")
    
    print("Waiting for data connection...")
    time.sleep(1)
    
    # Test basic connection
    print("Testing basic connection...")
    for i in range(50):
        latest_data = motive.get_last()
        if latest_data:
            print(f"✓ Connection established! Frame ID: {latest_data['frame_id']}")
            break
        time.sleep(0.1)
    else:
        print("✗ No data received. Check OptiTrack connection.")
        motive.stop()
        exit(1)
    
    # Create rigid body
    rigid_body = RigidBody(motive, rigid_body_name)
    
    # Setup OSC sender
    print(f"Setting up OSC sender to {args.osc_ip}...")
    sender = lt.OSCSender(args.osc_ip)
    
    print(f"Starting OSC streaming for rigid body '{rigid_body_name}' at {args.rate}Hz...")
    frame_count = 0
    
    try:
        while True:
            time.sleep(sleep_time)  # Use sleep_time for consistent update rate
            frame_count += 1
            
            # Update rigid body data
            rigid_body.update()
            
            # Get position and orientation data
            position = rigid_body.positions.get_last()
            euler_angles = rigid_body.euler_angles.get_last()
            
            # Only send if we have valid data (not zeros)
            if not position.any() == 0:
                # Send position data
                sender.send_message(f"/{rigid_body_name}_x", float(position[0]))
                sender.send_message(f"/{rigid_body_name}_y", float(position[1]))
                sender.send_message(f"/{rigid_body_name}_z", float(position[2]))
                
                # Send orientation data (euler angles)
                sender.send_message(f"/{rigid_body_name}_roll", float(euler_angles[0]))
                sender.send_message(f"/{rigid_body_name}_pitch", float(euler_angles[1]))
                sender.send_message(f"/{rigid_body_name}_yaw", float(euler_angles[2]))
                
                # Print status occasionally
                if frame_count % 100 == 0:
                    print(f"Streaming frame {frame_count}: pos={position}, euler={euler_angles}")
                    
    except KeyboardInterrupt:
        print("\nStopping OSC streaming...")
        motive.stop()

if __name__ == "__main__":
    main() 