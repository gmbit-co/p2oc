# `p2oc` (aka Pay to Open Channel)

![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)

**This software is still in beta (and so are all the present lightning node implementations!) so please use with caution.**

## Introduction

p2oc (Pay to Open Channel) is a protocol atop running Lightning Network nodes (presently [LND](https://github.com/lightningnetwork/lnd)) to allow a node to request an inbound channel of a given size ("fund amount") from another node in exchange for a fee ("premium amount") which can be paid immediately or gradually upon channel opening. The procedure presently involves 4 steps between participating nodes, but will be made more streamlined in the future. Under the hood, we are creating a custom funding transaction with multiple inputs by passing a [PSBT](https://github.com/bitcoin/bitcoin/blob/master/doc/psbt.md) back and forth between the two parties to build up this transaction.

### Requirements

* [LND](https://github.com/lightningnetwork/lnd) on `master`
  * Why? A required change to include the BIP 32 derivation path was added to LND via btcwallet dependency [3 months ago](35b4b237c997a5a57dcc8dc06a5f85aa703d6df6). A new release should be cut [mid-late May](https://github.com/lightningnetwork/lnd/projects/12). We personally have been using commit [6d66133](6d661334599ffa2a409ad6b0942328f9fd213d09)
* Python >= 3.6
* libsecp256k1. See [Dockerfile](./Dockerfile) how to install it.

### How It works

The pay to open channel protocol consists of 4 steps performed between a **Taker** (a node requesting inbound liquidity channel and paying a premium for it) and a **Maker** (a node providing outbound liquidity in exchange for premium):

1. Taker creates an offer which includes funding amount (inbound liquidity amount), premium amount, UTXOs to pay the premium, a change address, node address and a pubkey for 2-2 multisig of channel funding output. In addition, the offer specifies transaction fee<sup>1</sup> for the funding transaction. The offer is packaged as a PSBT packet and sent to the Maker. _How the PSBT packet is delivered to the Maker is currently outside of the scope of this protocol. It can be done over email, chat, programmatic API and so on._
2. Maker reviews the offer and, if they decide to accept it, they first complete the funding transaction<sup>2</sup> by adding their own UTXOs for the funding amount, their change address and 2-2 multisig for [the channel funding output](https://github.com/lightningnetwork/lightning-rfc/blob/master/03-transactions.md#funding-transaction-output). Then the Maker connects to the Taker's node, updates PSBT with complete but not yet signed funding transaction and sends the PSBT packet back to Taker.
3. Taker verifies that the funding transaction is correct. For example, they check that their inputs and outputs were included, that the channel funding output is correctly constructed with the right amount. Then they sign their inputs and open a pending channel with the Maker's node using the channel point of the funding transaction (`funding_tx_id:vout_id`). The channel will have the total capacity of funding amount + premium amount. The channel's capacity is split between Taker and Maker according to the terms of the offer: funding amount on Maker's side and premium amount on Taker's side. The PSBT packet is updated to include Taker's signatures and sent back to Maker for the final step.
4. Maker verifies that PSBT and the included funding transaction are correct. They also check that there is a pending channel with the Taker that points to the funding transaction and has the right balances between Maker and Taker<sup>3</sup>. They sign their inputs, finalize PSBT and publish the funding transaction. After the funding transaction is confirmed, the channel is fully open and active.


<sup>1</sup> Currently this fee is paid by the Taker, however the protocol can support splitting the fee between 2 participants

<sup>2</sup> In the most basic case the funding transaction will look the following:

```
                FUNDING TRANSACTION

+---------------------------------------------------+
|         INPUTS                   OUTPUTS          |
|  +------------------+    +---------------------+  |
|  |   Taker's UTXO   |    |                     |  |
|  | premium + tx fee |    |   Taker's change    |  |
|  |                  |    |                     |  |
|  +------------------+    +---------------------+  |
|                                                   |
|  +-------------------+   +---------------------+  |
|  |   Maker's UTXO    |   |                     |  |
|  |      funding      |   |   Maker's change    |  |
|  |                   |   |                     |  |
|  +-------------------+   +---------------------+  |
|                                                   |
|                          +---------------------+  |
|                          |   Channel funding   |  |
|                          |   2-2 multisig      |  |
|                          |   output            |  |
|                          +---------------------+  |
+---------------------------------------------------+
```

<sup>3</sup> Note that the Taker's balance would be slightly less than the premium because additional funds would be automatically reserved by  LND for the commitment transaction fees.

## How To Use

The procedure described above is carried out by the following commands (note the order and which party runs each command):

```bash
# Step 1 (run by Taker, requesting inbound channel)
#     E.g. Pay ~10USD (@50kUSD/BTC) premium in exchange for ~$2,000
$ p2oc createoffer --premium=20000 --fund=4000000
<offer_psbt>

# Step 2 (run by Maker, providing channel)
$ p2oc acceptoffer <offer_psbt>
<unsigned_psbt>

# Step 3 (run by Taker)
$ p2oc openchannel <unsigned_psbt>
<half_signed_psbt>

# Step 4 (run by Maker)
$ p2oc finalizeoffer <half_signed_psbt>
```

PSBT packet can be inspected using one of the following options:

```
p2oc inspect <psbt_base64>

bitcoin-cli decodepsbt <psbt_base64>
```

## Setup

### Option 1: Docker

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
### Option 2: pip

```bash
git clone <this_repo>
pip install .

p2oc --help
```

## Run

### Example 1: Running with [Umbrel](https://github.com/getumbrel/umbrel)

Here's an example of running `p2oc` within a more common environment like [Umbrel](...).

**Step 1: Setup Umbrel**

Download Umbrel according to the instructions for your system. Go through the setup process to create a wallet. Once you're able to get to the dashboard, stop Umbrel.

**Step 2: Update Umbrel Middleware**

Umbrel Middleware doesn't presently support newer versions of LND due to changes in wallet unlock handling. Use [this branch](https://github.com/JVillella/umbrel-middleware/tree/support-lnd-0.13-locked-wallet-error) to support updated LND versions.

```bash
# Assuming you're in the umbrel directory, cd ../ up a level
git clone git@github.com:JVillella/umbrel-middleware.git
git checkout
```

Then update Umbrel to point to this image.

```diff
middleware:
    container_name: middleware
-   image: getumbrel/middleware:v0.1.10@sha256:ff3d5929a506739286f296c803105cca9d83e73e9eb1b7c6833533e345d77736
+   image: getumbrel/manager
+   build:
+       context: ../umbrel-middleware
```

**Step 3: Update LND**

Because we require BIP 32 derivation maps which is in master of LND (see requirements above) but a few weeks away from release, we need to use `master`. Here's the easiest way to do that w/ Umbrel.

```bash
# Assuming you're in the umbrel directory, cd ../ up a level
git clone git@github.com:flywheelstudio/docker-lnd.git
# This repo is a clone of Umbrel's LND Dockerfile but with the ability to point to master
```

Now update Umbrel's docker-compose.yml to point to master LND,

```diff
lnd:
    container_name: lnd
-   image: lncm/lnd:v0.12.1@sha256:bdc442c00bc4dd4d5bfa42efd7d977bfe4d21a08d466c933b9cff7cfc83e0c0e
+   image: lncm/lnd
+       build:
+       context: ../docker-lnd/0.12
+       args:
+           VERSION: 6d66133
```

Then run `docker-compose build lnd`. Now you can start Umbrel back up again.

**Step 4: Get `p2oc`**

```bash
# Go to wherever you like to clone source on your machine
# `git clone <this_repo>` and `cd` into it
```

**Step 5: (Optional) Configure `p2oc` through a file**

For convenience, create the following file called `lnd.conf` (in this example we put it under `~/src/p2oc`) with the appropriate params for your system. If you don't do this, you'll have to pass these parameters manually each time you invoke `p2oc`.

```ini
[Application Options]
# LND host
rpclisten=lnd:10009
tlscertpath=/root/src/umbrel/lnd/tls.cert
adminmacaroonpath=/root/src/umbrel/lnd/data/chain/bitcoin/testnet/admin.macaroon

[Bitcoin]
bitcoin.testnet=1
```

**Step 6: Profit! (literally)**

At this point you can use `p2oc` either via docker or pip (here we'll demo with docker). In this example we'll pretend you're requesting an inbound channel (from a "maker"), so you're (aka the "taker") creating the offer.

```bash
docker build -t p2oc .

# Step 1 - Taker (you): Create offer, and send to maker
# E.g. Pay ~10USD (@50kUSD/BTC) premium in exchange for ~$2,000
docker run --rm -it -v /root/src/p2oc/lnd.conf:/lnd.conf -v /root/src/umbrel:/root/src/umbrel:ro --network=umbrel_main_network \
  p2oc -c lnd.conf createoffer --premium=20000 --fund=4000000

# Step 2 - Maker (them): Accepts offer
docker run --rm -it -v /root/src/p2oc/lnd.conf:/lnd.conf -v /root/src/umbrel:/root/src/umbrel:ro --network=umbrel_main_network \
  acceptoffer <offer>

# Step 3 - Taker: Open pending channel
docker run --rm -it -v /root/src/p2oc/lnd.conf:/lnd.conf -v /root/src/umbrel:/root/src/umbrel:ro --network=umbrel_main_network \
  openchannel <unsigned_psbt>

# Step 4 - Maker: Finalize and publish funding tx, opening channel
docker run --rm -it -v /root/src/p2oc/lnd.conf:/lnd.conf -v /root/src/umbrel:/root/src/umbrel:ro --network=umbrel_main_network \
  finalizeoffer <half_signed_psbt>

# Profit!
```

### Example 2: Running in provided docker test environment

Here's an example of running p2oc using the provided [docker-compose.yml](./docker-compose.yml) _testing environment_ among 2 peers to perform a double funded channel opening. Note: Instead of passing the network, host, etc. manually you can point to the `lnd.conf` file via `--configfile` (default location is `~/.lnd/lnd.conf`).

```bash
docker-compose up

docker exec -it p2oc python scripts/mine_and_fund.py --network="regtest"

# For convenience you can use --configfile to avoid having to pass these params manually.
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
