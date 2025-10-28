FROM python:3.10

WORKDIR /src

RUN apt-get update && \
    apt-get -y install \
        curl \
        gnupg2 \
        knot-dnsutils \
        net-tools && \
    rm -rf /var/lib/apt/lists/*

# Install additional packages
RUN apt-get -y install knot-dnsutils net-tools

COPY requirements.txt /src
RUN pip install -r requirements.txt

COPY istream_player istream_player
COPY scripts scripts
COPY setup.py .

RUN pip install .

ENTRYPOINT ["python3", "/src/wrapper.py"]
