# `p2oc` (aka Pay to Open Channel)

![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)

**This software is still in beta (and so are all the present lightning node implementations!) so please use with caution.**

## Introduction

p2oc (Pay to Open Channel) is a protocol atop running Lightning Network nodes (presently [LND](https://github.com/lightningnetwork/lnd)) to allow a node to request an inbound channel of a given size ("fund amount") from another node in exchange for a fee ("premium amount") which is paid immediately as part of the funding transaction. The procedure presently involves going back and forth 2x, but will be made more streamlined in the future. Under the hood, we are creating a custom funding transaction with multiple inputs by passing a PSBT back and forth between the two parties to build up this transaction.

### Requirements

* [LND](https://github.com/lightningnetwork/lnd) on `master`
  * Why? A required change to include the BIP 32 derivation path was added to LND via btcwallet dependency [3 months ago](35b4b237c997a5a57dcc8dc06a5f85aa703d6df6). A new release should be cut [mid-late May](https://github.com/lightningnetwork/lnd/projects/12). We personally have been using commit [6d66133](6d661334599ffa2a409ad6b0942328f9fd213d09)
* Python >= 3.6

### How To Use

Following is the order of commands to be run and by which party:

```
Step 1 (run by Taker, requesting inbound channel)
$ p2oc p2oc createoffer --premium=100000 --fund=1500000
<offer_psbt>

Step 2 (run by Maker, providing channel)
$ p2oc acceptoffer <offer_psbt>
<unsigned_psbt>

Step 3 (run by Taker)
$ p2oc openchannel <unsigned_psbt>
<half_signed_psbt>

Step 4 (run by Maker)
$ p2oc finalizeoffer <half_signed_psbt>
```

### `p2oc --help`

```
Usage: p2oc [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --configfile TEXT           The path to the LND config file (by default
                                  under ~/.lnd/lnd.conf). The host, network,
                                  tlscertpath, and adminmacaroonpath will be
                                  looked for in this config file. If those
                                  params are passed manually they will
                                  override what was found in the config file.

  -h, --host TEXT                 The host of your node.
  -n, --network [mainnet|testnet|simnet|regtest]
                                  The network your lightning node is running
                                  on.

  --tlscertpath TEXT              The path to the LND's tls certificate (by
                                  default under ~/.lnd/tls.cert).

  --adminmacaroonpath TEXT        The path to the LND's admin macaroon path
                                  (by default under ~/.lnd/data/chain/bitcoin/
                                  testnet/admin.macaroon).

  --help                          Show this message and exit.

Commands:
  createoffer    (Step 1) Create an offer to request an inbound funded
                 channel (of fund amount) in exchange for a fee (premium
                 amount). You can send this offer to another node operator for
                 them to accept and provide liquidity.

  acceptoffer    (Step 2) Accept an offer requesting an inbound funded
                 channel (of fund amount) of which you'd provide. In exchange
                 you'll receive an upfront fee (of premium amount).

  openchannel    (Step 3) With an accepted offer in-hand, create and
                 open the channel. It will be in pending state after this
                 command.

  finalizeoffer  (Step 4) Finalize the p2oc procedure by publishing
                 the funding transaction. This channel can begin to be used
                 after 6 confirmations.

  inspect        Inspect the p2oc payload at anytime to see the details of the
                 PSBT being passed back and forth.
```

## Setup

### Option 1: pip

```bash
git clone <this_repo>
pip install .

p2oc --help
```

### Option 2: Docker

You can also use the provided docker container with,
```bash
git clone <this_repo>
docker build -t p2oc .

# Example how to run p2oc on raspiblitz
docker run -it --rm \
    -v $(pwd):/src/p2oc \
    -v /mnt/hdd/lnd:/root/.lnd \
    --network=host \
    p2oc --network=testnet createoffer --premium=100000 --fund=1500000
```

## Run

Here's an example of running p2oc using the provided [docker-compose.yml](./docker-compose.yml) _testing environment_ among 2 peers to perform a double funded channel opening. Note: Instead of passing the network, host, etc. manually you can point to the `lnd.conf` file via `--configfile` (default location is `~/.lnd/lnd.conf`).

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
docker run --rm -it -v $PWD:/src/p2oc --entrypoint /bin/bash p2oc scripts/build-pb.sh
```

### Pushing to PyPi

```bash
pip install --upgrade build twine

# Make sure your ~/.pypirc is updated with your keys
#     https://packaging.python.org/tutorials/packaging-projects

# rm -rf build dist
python -m build

# Test Registry
python -m twine upload --repository testpypi dist/*

# Production Registry
python -m twine upload --repository pypi dist/*
```
