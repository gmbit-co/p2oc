FROM jupyter/minimal-notebook:8d32a5208ca1

ENV PYTHONPATH=/src/p2oc

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    libsecp256k1-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Install p2oc package
COPY . /src/p2oc
RUN cd /src/p2oc && pip install .[dev]
RUN mkdir -p /usr/local/lib/python3.8/site-packages && cd /usr/local/lib/python3.8/site-packages && python /src/p2oc/setup.py develop

USER $NB_UID

WORKDIR /notebooks
