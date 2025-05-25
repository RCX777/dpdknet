FROM ubuntu:24.04
LABEL maintainer="robertcnst02@gmail.com"
ENV TZ=Europe/BUCHAREST \
    DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get clean
RUN apt-get update -y && apt-get install -y \
    ca-certificates \
    git \
    net-tools \
    aptitude \
    build-essential \
    python3-setuptools \
    python3-dev \
    python3-pip \
    python3-venv \
    software-properties-common \
    ansible \
    curl \
    iptables \
    iputils-ping \
    sudo

# Install Docker
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
        https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt update -y && \
    apt install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin

COPY ./util/install-ovs-dpdk.sh /tmp/install-ovs-dpdk.sh
RUN /tmp/install-ovs-dpdk.sh && \
    rm -rf /tmp/install-ovs-dpdk.sh

# Add dpdk utils to path
ENV PATH="/usr/dpdk/bin:$PATH"

ENV OVS_SOCK_PATH='/var/run/openvswitch'
ENV OVS_DB_PATH='/etc/openvswitch'
ENV OVS_LOG_PATH='/tmp/openvswitch/logs'
ENV OVS_DATA='/usr/local/share/openvswitch'
ENV OVS_PIDFILE="$OVS_SOCK_PATH/ovs-vswitchd.pid"
ENV OVSDB_PIDFILE="$OVS_SOCK_PATH/ovsdb-server.pid"
ENV OVS_RUNDIR="$OVS_SOCK_PATH"

# Install dpdknet
COPY dist/ /tmp/dpdknet/
RUN pip3 install --break-system-packages /tmp/dpdknet/*.whl && \
    rm -rf /tmp/dpdknet

# Important: This entrypoint is required to start the OVS service
COPY ./docker/entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
