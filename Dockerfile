FROM python:3.8-buster

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libsecp256k1-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

ENV PYTHONPATH=/src/p2oc

COPY . /src/p2oc
WORKDIR /src/p2oc

RUN pip install .[dev]

# Workaround to support editable mode w/o having the volume mount overwrite the egg links
RUN cd /usr/local/lib/python3.8/site-packages && python /src/p2oc/setup.py develop

ENTRYPOINT ["p2oc"]
