FROM python:3.10

WORKDIR /src

RUN apt-get update && \
    apt-get -y install \
        linux-modules-extra-$(uname -r) \
        curl \
        gnupg2 \
        knot-dnsutils \
        kmod \
        net-tools \
        iproute2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /src
RUN pip install -r requirements.txt

COPY istream_player istream_player
COPY scripts scripts
COPY setup.py .
COPY wrapper.py wrapper.py

RUN pip install .

ENV PATH="/sbin:/usr/sbin:${PATH}"