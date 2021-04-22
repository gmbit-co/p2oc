FROM jupyter/minimal-notebook:8d32a5208ca1

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

USER $NB_UID

# should match lnd docker image
ARG LND_VERSION=v0.12.1-beta
RUN set -eux; \
    # git clone https://github.com/petertodd/python-bitcoinlib.git
    git clone https://github.com/flywheelstudio/python-bitcoinlib.git; \
    cd python-bitcoinlib; \
    git checkout 0.19.0.1-support; \
    pip3 install .; \
    pip3 install limit-order-book==2.0.0; \
    pip3 install grpcio grpcio-tools googleapis-common-protos; \
    # compile LND grpc protos
    # https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
    cd ..; \
    git clone https://github.com/lightningnetwork/lnd.git; \
    cd lnd; \
    git checkout $LND_VERSION; \
    cd ..; \
    git clone https://github.com/googleapis/googleapis.git; \
    mkdir ./lnrpc; \
    # protoc -I=./lnd/lnrpc $(find ./lnd/lnrpc/ -iname "*.proto") --python_out=./lnrpc;
    python3 -m grpc_tools.protoc --python_out=./lnrpc --grpc_python_out=./lnrpc \
        --proto_path=./googleapis --proto_path=./lnd/lnrpc  $(find ./lnd/lnrpc/ -iname "*.proto");

WORKDIR /notebooks
