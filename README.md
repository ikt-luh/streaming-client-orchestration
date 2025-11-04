# Dash Emulator Universal
This is an extension of iStreamPlayer for large scale streaming experiments in the RABBIT@Scale Project for SPIRIT.
Find the original iStreamPlayer [here](https://github.com/NetMedia-Sys-Lab/istream-player).

This repository contains code to run an ensemble of Docker containers for Streaming V-PCC encoded content from a DASH media server.

# Setup
Python
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ca-certificates curl gnupg lsb-release

# Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# IP Route
sudo apt install -y iproute2
```

TODO: Write scripts for that.
- Python >= 3.8 TODO
- `docker`  TODO
- `iproute2` (for traffic shaping via `tc`)  
- `sudo` access for network control 
- just TODO

To allow traffic shaping without password prompt:

```bash
sudo visudo
your_username ALL=(ALL) NOPASSWD: /usr/sbin/tc
your_username ALL=(ALL) NOPASSWD: /usr/sbin/ip
```

Download the 5G dataset:
```bash
    just download-bw-traces
```


## Running Experiments
A streaming Experiment with N Clients can be started through
```bash
just start-experiment <path_to_config>
```
you can find an [example config](./configs/experiment1_node1.yaml) for the parameters.























## How to build

```bash
# Install package
pip install .
```

## Running
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