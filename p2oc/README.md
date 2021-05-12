# `p2oc` (aka Pay to Open Channel)

![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)

`p2oc` (Pay to Open Channel) is a protocol atop running lightning network nodes (presently [LND](https://github.com/lightningnetwork/lnd)) to allow a node to request an inbound channel of a given size ("fund amount") from another node in exchange for a fee ("premium amount"). The procedure presently involves going back and forth 2x, but will be made more streamlined in the future. To kick off the process the peer ("taker") who wants an inbound channel from another peer ("maker") runs: `p2oc createoffer --premium=... --fund=...`.

<u>**This software is still in beta (and so are all the present lightning node implementations!) so please use with caution.**</u>

## Setup

```bash
git clone <this_repo>
pip install .
# Run p2oc commands
```

You can also use the provided docker container with,
```bash
...
```

## Run

Here's an example of running p2oc among 2 peers to perform a double funded channel opening.

```bash
docker-compose up

docker exec -it p2oc python scripts/mine_and_fund.py --network="regtest"

docker exec -it p2oc p2oc \
    --network="regtest" \
    --host="ali-lnd:10009" \
    --tlscertpath="/ali-lnd/tls.cert" \
    --adminmacaroonpath="/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    createoffer \
    --premium=100000 \
    --fund=1500000

docker exec -it p2oc p2oc \
    --network="regtest" \
    --host="bob-lnd:10009" \
    --tlscertpath="/bob-lnd/tls.cert" \
    --adminmacaroonpath="/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    acceptoffer \
    ...

docker exec -it p2oc p2oc \
    --network="regtest" \
    --host="ali-lnd:10009" \
    --tlscertpath="/ali-lnd/tls.cert" \
    --adminmacaroonpath="/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    openchannel \
    ...

docker exec -it p2oc p2oc \
    --network="regtest" \
    --host="bob-lnd:10009" \
    --tlscertpath="/bob-lnd/tls.cert" \
    --adminmacaroonpath="/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon" \
    finalizeoffer \
    ...

docker exec -it p2oc p2oc inspect \
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
black p2oc tests scripts
```

### Re-compile Protobufs

```bash
docker build -t p2oc .
docker run --rm -it -v $PWD:/src/p2oc --entrypoint /bin/bash p2oc build-pb.sh
```
