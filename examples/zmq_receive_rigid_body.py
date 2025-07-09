import lunar_tools as lt
import time
import argparse

# Example: ZMQ receiver for OptiTrack rigid body data

def main():
    parser = argparse.ArgumentParser(description='Receive ZMQ rigid body data')
    parser.add_argument('--ip', required=True, help='IP address to bind to (required)')
    parser.add_argument('--port', type=int, required=True, help='Port to bind to (required)')
    args = parser.parse_args()

    rigid_body_name = "B"
    signals = ['x', 'y', 'z', 'roll', 'pitch', 'yaw']

    print("Setting up ZMQ client...")
    client = lt.ZMQPairEndpoint(is_server=False, ip=args.ip, port=args.port)

    print(f"Listening for rigid body '{rigid_body_name}' ZMQ data on {args.ip}:{args.port}")
    print(f"Expected JSON keys: 'frame', {signals}")
    print("Press Ctrl+C to stop\n")

    frame_count = 0
    try:
        while True:
            time.sleep(0.1)  # 10Hz polling rate
            frame_count += 1

            msgs = client.get_messages()
            if msgs:
                for msg in msgs:
                    frame = msg.get('frame', frame_count)
                    pos = [msg.get(s) for s in signals[:3]]
                    ori = [msg.get(s) for s in signals[3:]]

                    print(f"Frame {frame}:")
                    print(f"  Position: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]")
                    print(f"  Orientation: [{ori[0]:.3f}, {ori[1]:.3f}, {ori[2]:.3f}] (roll, pitch, yaw)")
                    print("-" * 50)
            else:
                print(f"Frame {frame_count}: Waiting for ZMQ data...")

    except KeyboardInterrupt:
        print("\nStopping ZMQ receiver...")

if __name__ == "__main__":
    main() 