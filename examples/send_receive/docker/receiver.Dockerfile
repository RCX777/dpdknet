FROM ubuntu:24.04

ENV TZ=Europe/PARIS \
    DEBIAN_FRONTEND=noninteractive

COPY ./docker/build-dpdk.sh /tmp/build-dpdk.sh
RUN /tmp/build-dpdk.sh && rm -rf /tmp/build-dpdk.sh

RUN apt update -y && apt install -y \
    pkg-config

COPY ./apps /apps
COPY ./utils /utils

CMD [ "/utils/run-dpdk-vhost.sh", "/apps/receive/build/receive-shared" ]

