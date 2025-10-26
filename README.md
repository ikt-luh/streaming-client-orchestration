# Dash Emulator Universal

This version of the DASH Headless Player can play dash videos over several different configurations.

## Supported Features

- 360 degree videos
- Live Streaming
- QUIC and TCP supported
- Streaming from local file system
- Bandwidth throttled streaming
- 3 different ABR algorithms - Bandwidth-based, Buffer-based and Hybrid
- Downloaded file saver
- Statistics Collector
- 2 different BW Estimation methods - Segment-based and instantaneous

## System Requirements
- Python >= 3.8
- `docker`  
- `iproute2` (for traffic shaping via `tc`)  
- `sudo` access for network control 

## Add sudo rule
To allow traffic shaping without password prompt:
```bash
sudo visudo
your_username ALL=(ALL) NOPASSWD: /usr/sbin/tc
your_username ALL=(ALL) NOPASSWD: /usr/sbin/ip
```
## How to build

```bash
# Install package
pip install .
```

### How to Run
```bash
just start-experiment <number_of_containers> <duration_in_seconds> <lambda_of_distribution> <target_bandwidth> <id of node>
```

### Testing modes
```bash
# start and open one container interactively
just test-player

# start one container and load a custom CSV bandwidth profile
just test-csv <duration_in_seconds> <lambda> <path_to_csv_file>

# start one container with a fixed static bandwidth
just test-bandwidth <duration_in_seconds> <lambda> <bandwidth_in_kbit>
```