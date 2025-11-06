FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y iproute2 iptables bash && \
    rm -rf /var/lib/apt/lists/*

COPY switch.sh /app/switch.sh
RUN chmod +x /app/switch.sh

ENTRYPOINT ["/app/switch.sh"]