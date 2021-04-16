FROM jupyter/minimal-notebook:8d32a5208ca1

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

USER $NB_UID

RUN set -eux; \
    # git clone https://github.com/petertodd/python-bitcoinlib.git
    git clone https://github.com/flywheelstudio/python-bitcoinlib.git; \
    cd python-bitcoinlib; \
    git checkout simnet-params; \
    pip3 install .; \
    pip3 install limit-order-book==2.0.0

WORKDIR /notebooks
