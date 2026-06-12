FROM alpine:latest

RUN apk update && apk add --no-cache \
    bash \
    iproute2 \
    iputils \
    tcpdump \
    python3 \
    traceroute \
    iperf3 \
    net-tools \
    bind-tools \
    curl \
    wget \
    mtr \
    ethtool \
    bridge \
    busybox-extras \
    nmap \
    openssh-client \
    jq \
    vim

CMD ["/bin/sh"]
