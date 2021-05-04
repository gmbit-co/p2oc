# `p2oc` (aka Pay-To-Open-Channel)

![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)

## Setup

## Run

## Tests

```bash
docker-compose up
docker exec -it p2oc pytest
```

## Extras

### Re-compile Protobufs

```bash
docker build -t p2oc .
docker run --rm -it -v $PWD:/src/p2oc --entrypoint /bin/bash p2oc build-pb.sh
```
