# DASH Client Emulation based on istream-player
This is an extension of iStream-Player for streaming experiments in the RABBIT@Scale Project for SPIRIT.
Find the original iStream-Player [here](https://github.com/NetMedia-Sys-Lab/istream-player).

This repository allows to deploy multiple DASH Clients running on the same device for streaming experiments.
Each client is deployed in a container in conjunction with a switch container for link emulation. 

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


# Running Experiments
For running an experiment, adapt the experiment configurations in **./configs/**. 
Each configuration requires to link a client configuration, an example can be found [here](./ressources/1s_segments.yaml) 
A streaming Experiment with N Clients can be started through
```bash
just start-experiment <path_to_config>
```
you can find an [example config](./configs/experiment1_node1.yaml) for the parameters.



## Download Bandwidth Traces
```
cd resources/traces
wget https://users.ugent.be/~jvdrhoof/dataset-4g/logs/logs_all.zip
```

