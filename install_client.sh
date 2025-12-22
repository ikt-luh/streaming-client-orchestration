#!/usr/bin/env bash

sudo apt update
sudo apt install -y python3 python3-pip python3-venv ca-certificates curl gnupg lsb-release snapd git

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

# JUST
sudo snap install --edge --classic just
sudo snap set system homedirs=/users

# REPO
git clone -b main https://github.com/ikt-luh/streaming-client-orchestration.git
cd streaming-client-orchestration

sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker