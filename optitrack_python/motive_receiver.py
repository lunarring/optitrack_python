#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import numpy as np
import math
import time
import threading
import sys
import signal
# # from icecream import ic

# #from util import euler_from_quaternion
# sys.path.append("/home/lugo/git/NatNetSDK_4.1.0")

from optitrack_python.streaming.NatNetClient import NatNetClient


def compute_sq_distances(a, b):
    # Calculate differences using broadcasting
    diff = a[:, np.newaxis, :] - b[np.newaxis, :, :]
    # Calculate squared Euclidean distances
    dist_squared = np.sum(diff ** 2, axis=2)
    ## Take square root to get Euclidean distances
    # distances = np.sqrt(dist_squared)
    
    # Create dictionary to store dist_squared with index pairs
    distance_dict = {
        (i_a, i_b): dist_squared[i_a, i_b] 
        for i_a in range(dist_squared.shape[0]) 
        for i_b in range(dist_squared.shape[1])
    }
    distance_dict = dict(sorted(distance_dict.items(), key=lambda item: item[1]))
    return distance_dict


class MotiveReceiver:
    def __init__(
        self, 
        server_ip, 
        client_ip="0.0.0.0",  # Default to all interfaces to receive multicast
        max_buffer_size=100000, 
        start_process=True, 
        do_record_streaming=False, 
        do_mock_streaming=False, 
        fn_mock='streaming_mock.pkl'
    ):
        self.server_ip = server_ip
        self.client_ip = client_ip
        self.max_buffer_size = max_buffer_size
        self.marker_data = []
        self.lock = threading.Lock()
        self.running = True
        self.sleep_time = 0.000001
        self.list_raw_packets = []
        self.list_dict_packets = []
        
        
        self.v_last_time = 0
        self.v_sampling_time = 0.01
        self.last_frame_id = 0
        self.list_labels = []
        self.dict_label_idx = {}
        self.set_labels = set()
        self.list_unlabeled = []
        self.list_timestamps = []
        
        self.max_nr_markers = 999
        self.positions = np.zeros([self.max_buffer_size, self.max_nr_markers, 3])*np.nan
        self.velocities = np.zeros([self.max_buffer_size, self.max_nr_markers, 3])
        self.pos_idx = 0
        self.last_timestamp = None
                        
        self.do_record_streaming = do_record_streaming
        self.do_mock_streaming = do_mock_streaming
        self.fn_mock = fn_mock
        # self.rigid_body_positions = {label:[] for label in self.rigid_body_labels}
        if start_process:
            self.start_process()

    def get_last_by_model(self, simbly, model_name=""):
        if model_name in self.list_dict_packets[-1][simbly].keys():
            return self.list_dict_packets[-1][simbly][model_name]
        else:
            return self.list_dict_packets[-1][simbly]

    def get_last_timestamp(self):
        if len(self.list_dict_packets) > 0:
            return self.list_dict_packets[-1]['timestamp']
        else:
            return 0
                

    def start_process(self):
        self.thread = threading.Thread(target=self.get_data)
        self.thread.start()

    def get_data(self):
        try:
            optionsDict = {}
            optionsDict["clientAddress"] = self.client_ip
            optionsDict["serverAddress"] = self.server_ip
            optionsDict["use_multicast"] = True

            self.streaming_client = NatNetClient()
            if self.do_record_streaming:
                self.streaming_client.set_record_streaming(fn_mock=self.fn_mock)
            if self.do_mock_streaming:
                self.streaming_client.set_mock_streaming(fn_mock=self.fn_mock)
            self.streaming_client.set_client_address(optionsDict["clientAddress"])
            self.streaming_client.set_server_address(optionsDict["serverAddress"])
            self.streaming_client.set_use_multicast(optionsDict["use_multicast"])
            self.streaming_client.new_frame_listener = self.process_packet
                
            is_running = self.streaming_client.run()
            if not is_running:
                print("ERROR: Could not start streaming client.")
                return
        except Exception as e:
            print(f"ERROR: Exception in streaming client: {e}")
            return
            

    def save_packet(self, packet_content):
        self.list_raw_packets.append(packet_content)
        
    def normalizer_data(self, dict_data):
        labels_rows = [_["model_name"] for _ in dict_data["marker_sets_labeled_data"]]
        dict_data["rigid_bodies_full"] = {}

        for __ in dict_data["rigid_bodies"]:
            id_ = __["id_num"]-1
            out = __
            out["model_name"] = labels_rows[id_]
            out["markers"] = dict_data["marker_sets_labeled_data"][id_]["marker_pos_list"]
            if len(dict_data["labeled_markers"])-1 >= id_ and id_ >= 0:
                #print("id",id_)
                #print(dict_data["labeled_markers"])
                out["labeled_markers"] = dict_data["labeled_markers"][id_]
            model_name = out["model_name"].decode()
            del out["model_name"]
            dict_data["rigid_bodies_full"][model_name] = out
        return dict_data
    
    def process_packet(self, data_dict):
        #print(data_dict["mocap_data"].skeleton_data.__dict__)
        if self.do_mock_streaming:
            dict_data = {
                "frame_id": data_dict["frame_number"],
                "timestamp" : data_dict["mocap_data"].suffix_data.timestamp,
                "marker_sets_unlabeled_data" : data_dict["mocap_data"].marker_set_data.unlabeled_markers.__dict__,
                "unlabeled_markers" : data_dict["mocap_data"].legacy_other_markers.__dict__,
                "marker_sets_labeled_data" : [_.__dict__ for _ in data_dict["mocap_data"].marker_set_data.marker_data_list],
                "unlabeled_markers" : data_dict["mocap_data"].legacy_other_markers.__dict__,
                "labeled_markers" : [_.__dict__ for _ in data_dict["mocap_data"].labeled_marker_data.labeled_marker_list],
                "rigid_bodies" : [_.__dict__ for _ in data_dict["mocap_data"].rigid_body_data.rigid_body_list],
                # "asset_data" : data_dict["mocap_data"].asset_data.__dict__,
                "asset_data" : None,
                "skeletons_list" : [_.__dict__ for _ in data_dict["mocap_data"].skeleton_data.skeleton_list]
            }
        else:
            dict_data = {
                "frame_id": data_dict["frame_number"],
                "timestamp" : data_dict["mocap_data"].suffix_data.timestamp,
                "marker_sets_unlabeled_data" : data_dict["mocap_data"].marker_set_data.unlabeled_markers.__dict__,
                "unlabeled_markers" : data_dict["mocap_data"].legacy_other_markers.__dict__,
                "marker_sets_labeled_data" : [_.__dict__ for _ in data_dict["mocap_data"].marker_set_data.marker_data_list],
                "unlabeled_markers" : data_dict["mocap_data"].legacy_other_markers.__dict__,
                "labeled_markers" : [_.__dict__ for _ in data_dict["mocap_data"].labeled_marker_data.labeled_marker_list],
                "rigid_bodies" : [_.__dict__ for _ in data_dict["mocap_data"].rigid_body_data.rigid_body_list],
                "asset_data" : data_dict["mocap_data"].asset_data.__dict__,
                "skeletons_list" : [_.__dict__ for _ in data_dict["mocap_data"].skeleton_data.skeleton_list]
            }
            
        #if len(dict_data["skeletons_list"]) > 0:
        for ii,_ in enumerate(dict_data["skeletons_list"]):
            if "rigid_body_list" in _.keys():
                for i,__ in enumerate(_["rigid_body_list"]):
                    dict_data["skeletons_list"][ii]["rigid_body_list"][i] = __.__dict__
        #print(dict_data["skeletons_list"])
        dict_data = self.normalizer_data(dict_data)
        self.list_dict_packets.append(dict_data)
        

    def stop(self):
        print("stopping process!")
        self.running = False
        if hasattr(self, 'streaming_client') and self.streaming_client:
            self.streaming_client.shutdown()
        self.thread.join()
        
    def get_last(self, label=None):
        if len(self.list_dict_packets) == 0:
            return None
        else:
            if label is None:
                return self.list_dict_packets[-1]
            else:
                if label in self.list_dict_packets[-1].keys():
                    return self.list_dict_packets[-1][label]
                else:
                    return None


if __name__ == "__main__":
    # Create a MotiveReceiver instance with the server IP
    motive = MotiveReceiver(server_ip="10.40.49.47")
    
    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nStopping receiver...")
        motive.stop()
        print("Shutdown complete.")
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait a moment for connection to establish
    import time
    time.sleep(1)
    
    # Keep the script running to receive and display data
    try:
        print("Receiving data from OptiTrack. Press Ctrl+C to stop.")
        print("Waiting for data...")
        
        while True:
            latest_data = motive.get_last()
            if latest_data:
                # Print all frames with all rigid bodies
                print(f"\nFrame ID: {latest_data['frame_id']}")
                print(f"Timestamp: {latest_data['timestamp']}")
                if 'rigid_bodies_full' in latest_data and latest_data['rigid_bodies_full']:
                    print("\nRigid Bodies:")
                    for name, body in latest_data['rigid_bodies_full'].items():
                        pos = body.get('pos')
                        print(f"  {name}: Position {pos}")
                else:
                    print("No rigid bodies detected")
            else:
                print(".", end="", flush=True)

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopping receiver...")
        motive.stop()
        print("Shutdown complete.")
        
