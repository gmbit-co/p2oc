#!/usr/bin/python
import os
import argparse

import bitcoin

from p2oc.lnd_rpc import LndRpc, lnmsg
from p2oc.address import create_dummy_p2wpkh_address
from p2oc.btc_rpc import Proxy, Config

taker = LndRpc(
    config_overrides={
        "host": "ali-lnd:10009",
        "tlscertpath": "/ali-lnd/tls.cert",
        "adminmacaroonpath": "/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon",
    }
)


maker = LndRpc(
    config_overrides={
        "host": "bob-lnd:10009",
        "tlscertpath": "/bob-lnd/tls.cert",
        "adminmacaroonpath": "/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon",
    }
)

parser = argparse.ArgumentParser()
parser.add_argument("--network", default="regtest", type=str)
args = parser.parse_args()

bitcoin.SelectParams(args.network)

btc_rpc = Proxy(
    config=Config(
        rpcuser=os.environ["BTCD_RPCUSER"],
        rpcpassword=os.environ["BTCD_RPCPASS"],
        rpcconnect=os.environ["BTCD_RPCHOST"],
        rpcport=os.environ["BTCD_RPCPORT"],
    )
)

address_type = lnmsg.AddressType.WITNESS_PUBKEY_HASH
dummy_address = create_dummy_p2wpkh_address()
maker_address = maker.lnd.NewAddress(lnmsg.NewAddressRequest(type=address_type))
taker_address = taker.lnd.NewAddress(lnmsg.NewAddressRequest(type=address_type))

# Mine and fund wallets
_ = list(btc_rpc.generatetoaddress(400, dummy_address))
_ = list(btc_rpc.generatetoaddress(10, maker_address.address))
_ = list(btc_rpc.generatetoaddress(10, taker_address.address))
_ = list(btc_rpc.generatetoaddress(120, dummy_address))

print(
    f"""Block Height: {btc_rpc.getblockcount()}

Balances:

Taker: {taker.lnd.WalletBalance(lnmsg.WalletBalanceRequest())}

Maker: {maker.lnd.WalletBalance(lnmsg.WalletBalanceRequest())}"""
)
