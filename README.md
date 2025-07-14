# OptiTrack Python

A modern Python client library for OptiTrack's NatNet streaming protocol, enabling real-time motion capture data retrieval from OptiTrack systems.

## Features

- 🚀 **Real-time streaming** - Receive motion capture data in real-time from OptiTrack systems
- 🎯 **Rigid body tracking** - Easy-to-use rigid body position and orientation tracking
- 📊 **Multiple data formats** - Support for labeled/unlabeled markers, skeletons, and assets
- 🔌 **Multiple protocols** - Built-in OSC and ZeroMQ integration examples
- 🛠️ **Diagnostic tools** - Frame drop detection and tracking diagnostics
- 📈 **Visualization** - Optional pygame-based real-time position visualization

## Installation

```bash
pip install git+https://github.com/yourusername/optitrack_python.git
```

### Dependencies
- Python 3.10+
- numpy
- Optional: pygame (for visualization), python-osc, zmq

## Quick Start

```python
from optitrack_python.streaming.NatNetClient import NatNetClient

def receive_frame(data_dict):
    print(f"Frame {data_dict['frame_number']}: {len(data_dict['mocap_data'].rigid_body_data.rigid_body_list)} rigid bodies")

# Connect to OptiTrack server
client = NatNetClient()
client.set_server_address("10.40.49.47")  # Your OptiTrack server IP
client.new_frame_listener = receive_frame
client.run()
```

## Examples

### Basic Streaming

#### `hello_streaming_client.py`
Basic example showing how to connect and receive all motion capture data:
```bash
python examples/hello_streaming_client.py
```

### Rigid Body Tracking

#### `print_rigid_body.py`
Track a specific rigid body with optional pygame visualization:
```bash
# Track rigid body "A" with visualization
python examples/print_rigid_body.py -n A -s 10.40.49.47 -p

# Track without visualization
python examples/print_rigid_body.py -n A --no-pygame
```

### Protocol Integration

#### OSC (Open Sound Control)
Receive and send rigid body data via OSC:
```bash
# Receive OSC messages
python examples/osc_receive_rigid_body.py

# Send rigid body data as OSC messages
python scripts/osc_send_rigid_body.py
```

#### ZeroMQ
High-performance message queuing:
```bash
# Receive via ZeroMQ
python examples/zmq_receive_rigid_body.py

# Send via ZeroMQ
python scripts/zmq_send_rigid_body.py
```

## High-Level API

### MotiveReceiver
The main class for receiving motion capture data:

```python
from optitrack_python.motive_receiver import MotiveReceiver

# Create receiver
motive = MotiveReceiver(server_ip="10.40.49.47")

# Get latest data
latest_frame = motive.get_last()
timestamp = motive.get_last_timestamp()

# Access rigid bodies by model name
rigid_body_data = motive.get_last_by_model("rigid_bodies_full", "MyRigidBody")
```

### RigidBody
Simplified interface for tracking individual rigid bodies:

```python
from optitrack_python.rigid_body import RigidBody
from optitrack_python.motive_receiver import MotiveReceiver

motive = MotiveReceiver(server_ip="10.40.49.47")
rb = RigidBody(motive, "A")  # Track rigid body named "A"

# Get position and orientation
position = rb.get_position()  # [x, y, z]
rotation = rb.get_rotation()  # [qx, qy, qz, qw]
```

## Diagnostic Tools

### Frame Drop Detection
Monitor streaming performance and detect dropped frames:
```bash
python diagnostics/detect_frame_drops.py
```

### Rigid Body Tracker
Advanced rigid body tracking with detailed output:
```bash
python diagnostics/rigid_body_tracker.py
```

## Project Structure

```
optitrack_python/
├── optitrack_python/          # Main package
│   ├── streaming/             # Core NatNet streaming implementation
│   ├── motive_receiver.py     # High-level data receiver
│   └── rigid_body.py          # Rigid body tracking utilities
├── examples/                  # Usage examples
├── scripts/                   # Utility scripts for sending data
├── diagnostics/               # Diagnostic and debugging tools
└── logs/                      # Log files directory
```

## Configuration

### Server Connection
Configure your OptiTrack server connection:

```python
# Default localhost connection
client = NatNetClient()

# Custom server
client = NatNetClient()
client.set_server_address("192.168.1.100")
client.set_client_address("192.168.1.50")
client.set_use_multicast(True)
```

### Data Access
Access different types of motion capture data:

```python
def process_frame(data_dict):
    mocap_data = data_dict["mocap_data"]
    
    # Rigid bodies
    rigid_bodies = mocap_data.rigid_body_data.rigid_body_list
    
    # Labeled markers
    labeled_markers = mocap_data.labeled_marker_data.labeled_marker_list
    
    # Unlabeled markers  
    unlabeled_markers = mocap_data.legacy_other_markers
    
    # Skeletons
    skeletons = mocap_data.skeleton_data.skeleton_list
```

## Recording and Playback

Record streaming data for later analysis:
```python
motive = MotiveReceiver(
    server_ip="10.40.49.47",
    do_record_streaming=True,
    fn_mock="my_recording.pkl"
)
```

Playback recorded data:
```python
motive = MotiveReceiver(
    server_ip="10.40.49.47", 
    do_mock_streaming=True,
    fn_mock="my_recording.pkl"
)
```

## License

Apache License 2.0 - see LICENSE file for details.

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

