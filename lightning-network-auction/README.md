# Setup and Running

```shell
docker-compose up
```


**TODO: update instructions below**

Run Nth lnd container

```shell
$ export NETWORK="simnet"
$ export RPCUSER=satoshin
$ export RPCPASS=deadbeef
$ export INSTANCE=1
$ docker volume create lnd_${NETWORK}_${INSTANCE}
$ docker-compose run -d --name ln-node-${NETWORK}-${INSTANCE} -p ${INSTANCE}9735:9735 -v lnd_${NETWORK}_${INSTANCE}:/root/.lnd lnd
$ docker exec -i -t ln-node-${NETWORK}-${INSTANCE} bash
```

```shell
ln-node $ lncli --network=$NETWORK newaddress np2wkh
ln-node $ lncli --network=$NETWORK walletbalance
```

Setup channels

```shell
# "identity_pubkey" and ip address from other party: `lncli --network=$NETWORK getinfo`
# tip: run `docker inspect <container-name> | grep IPAddress` to get IP of docker container
ln-node $ lncli --network=$NETWORK connect 029953b182bde57391e3dd5f164fca35ddf40409d7960b11f195748d3c9a3ed615@4.tcp.ngrok.io:13737
# see that connection worked with `lncli --network=$NETWORK listpeers`
ln-node $ lncli --network=$NETWORK openchannel --node_key=029953b182bde57391e3dd5f164fca35ddf40409d7960b11f195748d3c9a3ed615 --local_amt=20000
# see that channel was opened with `lncli --network=$NETWORK listchannels`
# "pay_req" from other party: `lncli --network=$NETWORK addinvoice --amt=10000`
ln-node $ lncli --network=$NETWORK sendpayment --pay_req=lntb50n1psxur25pp5ppperfekkrau7mfelngsmlck3tqpaqrw7ylda3thu360akveppqsdqqcqzpgsp5y6zwv7l7vuc0vdmxsf05dvz6qjxjtqfks97hq6a0z8cf30wrqf6q9qyyssqe2tt2g6u7sz77c633gepty4n9drc3k5q96u89l7svtjpnkjc5ld8aqn2awv5n5xv0pkz3z05aw2wav5297yl0dd8kct088fuyurl3kgpwx8etc
# check new balance with `lncli --network=$NETWORK channelbalance`
# "channel_point" (<funding_txid>:<output_index>) from `lncli --network=$NETWORK listchannels`
ln-node $ lncli --network=$NETWORK closechannel --funding_txid=3e7998c6d356cfd3d1d83474894846dc2ee062d4b6e623c56319a924c08707aa --output_index=0
# confirm locked funds were released with `lncli --network=$NETWORK walletbalance`
```

## Extras

**Running with Neutrino backend**

```shell
# Setup LND w/ BTC light client
$ export NETWORK="simnet"

$ docker volume create ${NETWORK}_lnd_light
$ docker-compose run -d --name ln-node-light-${NETWORK} --volume ${NETWORK}_lnd_light:/root/.lnd lnd \
    --bitcoin.${NETWORK} --bitcoin.node=neutrino --routing.assumechanvalid

# Check that we're at the appropriate block height (>1.97M)
$ docker logs -f ln-node-light-${NETWORK} | grep "at height="

$ docker exec -i -t ln-node-light-${NETWORK} bash
```

**Testnet faucets**

- https://testnet-faucet.mempool.co/
- https://onchain.io/bitcoin-testnet-faucet
- https://bitcoinfaucet.uo1.net/send.php

**Communicating with btcd over curl**

```shell
curl --key ../certs/rpc.key --cacert ../certs/rpc.cert --user satoshin:deadbeef --data-binary '{"jsonrpc": "1.0", "id":"curltest", "method": "getblockchaininfo", "params": [] }' -H 'content-type: text/plain;' https://127.0.0.1:18554

curl --user satoshin:deadbeef --data-binary '{"jsonrpc": "1.0", "id":"curltest", "method": "getblockchaininfo", "params": [] }' -H 'content-type: text/plain;' http://127.0.0.1:28554
```
