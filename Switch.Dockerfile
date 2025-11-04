# Simple switch container for bandwidth shaping
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y iproute2 iptables && \
    rm -rf /var/lib/apt/lists/*

# Enable IPv4 forwarding and apply bandwidth limit
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["sysctl -w net.ipv4.ip_forward=1 && \
      iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE && \
      tc qdisc add dev eth0 root tbf rate 4mbit burst 32kbit latency 400ms && \
      echo 'Switch up with 4mbit shaping' && \
      sleep infinity"]
