#!/usr/bin/env python3

import os
import subprocess
import sys
import csv
import time
from pathlib import Path
from typing import List
from datetime import datetime
import argparse

control_file = Path(os.getenv("CONTROL_FILE", "./control/run.flag"))
ready_file = Path("control/ready.flag")


class BandwidthController:
    def __init__(self, count: int, csv_files: List[str], static_bandwidth: float = None):
        self.count = count
        self.csv_files = csv_files
        self.static_bandwidth = static_bandwidth
        self.veth_interfaces = []
        self.container_names = []
        self.container_csv_map = {}
        self.csv_data = {}
    
    # check if csv file exists
    def validate_csv_files(self):
        for csv_file in self.csv_files:
            if not Path(csv_file).exists():
                print(f"file not found: {csv_file}")
                sys.exit(1)
    
    # get host-side veth interfaces corresponding to a containers eth0
    def get_container_veth(self, container_id: str) -> str:
        # get container pid
        result = subprocess.run(
            ['docker', 'inspect', '-f', '{{.State.Pid}}', container_id],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        pid = result.stdout.strip()
        if not pid or pid == '0':
            return None

        # get index of host veth interface
        result = subprocess.run(
            ['docker', 'exec', container_id, 'cat', '/sys/class/net/eth0/iflink'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        if result.returncode != 0:
            return None

        if_index = result.stdout.strip()

        # list all host interfaces
        result = subprocess.run(
            ['ip', '-o', 'link'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # return interface name which matches index and iflink
        for line in result.stdout.splitlines():
            if line.startswith(f"{if_index}:"):
                veth = line.split()[1].split('@')[0].rstrip(':')
                return veth

        return None
    
    # collect and map veth interfaces    
    def collect_veth_interfaces(self):
        
        for i in range(self.count):
            project_name = f"istream_player_{i}"
            
            #get container id
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'label=com.docker.compose.project={project_name}', '-q'],
                capture_output=True, text=True
            )
            
            container_ids = result.stdout.strip().split('\n')
            
            for container_id in container_ids:
                if not container_id:
                    continue
                
                veth = self.get_container_veth(container_id)
                
                if veth:
                    # get container name
                    result = subprocess.run(
                        ['docker', 'inspect', '-f', '{{.Name}}', container_id],
                        capture_output=True, text=True
                    )
                    container_name = result.stdout.strip().lstrip('/')
                    
                    self.veth_interfaces.append(veth)
                    self.container_names.append(container_name)
                    print(f"[{i}] Container: {container_name} -> veth: {veth}")
        
        num_containers = len(self.veth_interfaces)
        
        if num_containers == 0:
            print("no containers found")
            sys.exit(1)
        
        if not self.static_bandwidth: 
            num_csv_files = len(self.csv_files)
            # assign each container a csv file 
            for i in range(num_containers):
                csv_index = i % num_csv_files  # just iterate over the files repeatedly
                self.container_csv_map[i] = self.csv_files[csv_index]
                
                print(f"container {i} ({self.container_names[i]}) -> {self.csv_files[csv_index]}")
        else:
            print(f"container {i} ({self.container_names[i]}) -> {self.static_bandwidth} in kbit/s")
    
    # converts csv timestamp to unix timestamp (seconds since epoch)
    def parse_timestamp(self, timestamp_str: str) -> float:
        try:
            dt = datetime.strptime(timestamp_str, "%Y.%m.%d_%H.%M.%S")
            return dt.timestamp()
        except ValueError:
            return 0.0
    
    # load csv data
    def load_csv_data(self):
        
        for i in range(len(self.veth_interfaces)):
            csv_file = self.container_csv_map[i]
            
            timestamps = []
            bandwidths = []
            
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                
                first_timestamp = None
                
                for row in reader:
                    try:
                        raw_timestamp = row['Timestamp']
                        bandwidth = int(row['DL_bitrate'])
                        
                        if bandwidth > 0:
                            total_seconds = self.parse_timestamp(raw_timestamp)
                            
                            if first_timestamp is None:
                                first_timestamp = total_seconds
                            
                            relative_time = total_seconds - first_timestamp
                            
                            if relative_time >= 0:
                                timestamps.append(relative_time)
                                bandwidths.append(bandwidth)
                    except (KeyError, ValueError):
                        continue
            
            self.csv_data[i] = {
                'timestamps': timestamps,
                'bandwidths': bandwidths,
                'length': len(timestamps),
                'current_index': 0
            }
    # set bandwidth
    def set_bandwidth(self, veth: str, bandwidth: int):
        # remove previous rule
        subprocess.run(
            ['sudo', 'tc', 'qdisc', 'del', 'dev', veth, 'root'],
            stderr=subprocess.DEVNULL
        )
        
        # set new bandwidth
        subprocess.run(
            ['sudo', 'tc', 'qdisc', 'add', 'dev', veth, 'root', 'tbf',
             'rate', f'{bandwidth}kbit', 'burst', '32kbit', 'latency', '400ms'],
            capture_output=True, text=True
        )
    
    def run(self):
        # signal start of bandwidth control     
        ready_file.parent.mkdir(exist_ok=True)
        ready_file.write_text("1")
        
        start_time = time.time()
        
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            for i in range(len(self.veth_interfaces)):
                veth = self.veth_interfaces[i]
                data = self.csv_data[i]
                
                active_file = Path(f"control/active_{i}.flag")
                if not active_file.exists() or active_file.read_text().strip() != "1":
                    # skip bandwidth control of inactive containers
                    continue
                
                current_idx = data['current_index']
                
                if current_idx < data['length']:
                    target_time = data['timestamps'][current_idx]
                    
                    # update bandwidth based
                    if elapsed >= target_time:
                        bandwidth = data['bandwidths'][current_idx]
                        
                        self.set_bandwidth(veth, bandwidth)
                        
                        print(f"[{elapsed:.2f}s] {self.container_names[i]}: {bandwidth} kbit/s")
                        
                        data['current_index'] += 1
                        
                        # restart bandwidth profile if too short
                        if data['current_index'] >= data['length']:
                            print(f"container {i}: restart bandwidth profile")
                            data['current_index'] = 0
                            start_time = time.time()
            time.sleep(0.1)

    def run_static(self, bandwidth: int):
        # signal start of bandwidth control     
        ready_file.parent.mkdir(exist_ok=True)
        ready_file.write_text("1")
        veth = self.veth_interfaces[0]
        self.set_bandwidth(veth, bandwidth)

def main():
    parser = argparse.ArgumentParser(description='tc bandwidth control script')
    parser.add_argument('--count', type=int, required=True, help='number of containers')
    parser.add_argument('--csv-files', nargs='+', help='csv files for bandwidth control')
    parser.add_argument('--bandwidth', type=int, help='static bandwidth in kbit/s')
    
    args = parser.parse_args()
    
    count = args.count
    
    print(f"container count: {count}")
    
    if args.bandwidth:
        # static bandwidth
        print(f"using static bandwidth: {args.bandwidth} kbit/s")
        controller = BandwidthController(count, [], static_bandwidth=args.bandwidth)
        controller.collect_veth_interfaces()
        controller.run_static(args.bandwidth)
    else:
        # csv bandwidth
        csv_files = args.csv_files
        print("csv files:\n" + "\n".join(f"  - {f}" for f in csv_files))
        controller = BandwidthController(count, csv_files)
        controller.validate_csv_files()
        controller.collect_veth_interfaces()
        controller.load_csv_data()
        controller.run()


if __name__ == "__main__":
    main()