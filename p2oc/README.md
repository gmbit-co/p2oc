# `p2oc` (aka Pay-To-Open-Channel)

![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)

## Run

Here's an example of running p2oc among 2 peers to perform a double funded channel opening.
```
docker exec -it p2oc p2oc createoffer \
    --premium=10_000 \
    --fund=500_000 \
    --network="regtest" \
    --host="ali-lnd:10009" \
    --tlscertpath="/ali-lnd/tls.cert" \
    --adminmacaroonpath="/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon"

docker exec -it p2oc p2oc acceptoffer \
    --network="regtest" \
    --host="bob-lnd:10009" \
    --tlscertpath="/bob-lnd/tls.cert" \
    --adminmacaroonpath="/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    ...

docker exec -it p2oc p2oc openchannel \
    --network="regtest" \
    --host="ali-lnd:10009" \
    --tlscertpath="/ali-lnd/tls.cert" \
    --adminmacaroonpath="/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    ...

docker exec -it p2oc p2oc finalizeoffer \
    --network="regtest" \
    --host="bob-lnd:10009" \
    --tlscertpath="/bob-lnd/tls.cert" \
    --adminmacaroonpath="/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    ...
```
## Tests

```bash
docker-compose up
docker exec -it p2oc pytest
```

## Extras

### Formatting

```
black p2oc tests
```

### Re-compile Protobufs

```bash
docker build -t p2oc .
docker run --rm -it -v $PWD:/src/p2oc --entrypoint /bin/bash p2oc build-pb.sh
```
