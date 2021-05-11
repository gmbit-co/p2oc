import os
import time
import pytest

import bitcoin

import p2oc
from p2oc.address import create_dummy_p2wpkh_address
from p2oc.lnd_rpc import LndRpc, lnmsg
from p2oc.btc_rpc import Proxy, Config


@pytest.fixture
def network():
    return "regtest"


@pytest.fixture
def btc_rpc(network):
    bitcoin.SelectParams(network)
    btc_rpc = Proxy(
        config=Config(
            rpcuser=os.environ["BTCD_RPCUSER"],
            rpcpassword=os.environ["BTCD_RPCPASS"],
            rpcconnect=os.environ["BTCD_RPCHOST"],
            rpcport=os.environ["BTCD_RPCPORT"],
        )
    )
    return btc_rpc


@pytest.fixture
def taker(btc_rpc):
    return LndRpc(
        config_overrides={
            "host": "ali-lnd:10009",
            "tlscertpath": "/ali-lnd/tls.cert",
            "adminmacaroonpath": "/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon",
        }
    )


@pytest.fixture
def maker(btc_rpc):
    return LndRpc(
        config_overrides={
            "host": "bob-lnd:10009",
            "tlscertpath": "/bob-lnd/tls.cert",
            "adminmacaroonpath": "/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon",
        }
    )


def test_double_funded_channel_open(maker, taker, btc_rpc):
    premium_amount = 100000
    fund_amount = 16000000

    address_type = lnmsg.AddressType.WITNESS_PUBKEY_HASH
    dummy_address = create_dummy_p2wpkh_address()
    maker_address = maker.lnd.NewAddress(lnmsg.NewAddressRequest(type=address_type))
    taker_address = taker.lnd.NewAddress(lnmsg.NewAddressRequest(type=address_type))

    # Mine and fund wallets
    _ = list(btc_rpc.generatetoaddress(400, dummy_address))
    _ = list(btc_rpc.generatetoaddress(10, maker_address.address))
    _ = list(btc_rpc.generatetoaddress(10, taker_address.address))
    _ = list(btc_rpc.generatetoaddress(120, dummy_address))
    time.sleep(8)

    # Taker creates offer (to request inbound liquidity in exchange for a fee [the premium])
    offer_psbt = p2oc.create_offer(premium_amount, fund_amount, taker)

    # Maker accepts offer and sends reply
    unsigned_psbt = p2oc.accept_offer(offer_psbt, maker)

    # Taker checks offer reply and opens pending channel
    half_signed_psbt = p2oc.open_channel(unsigned_psbt, taker)

    # Maker checks pending channel reply, signs and commits funding tx
    p2oc.finalize_offer(half_signed_psbt, maker)

    # Confirm channel got oppened (send)
    _ = list(btc_rpc.generatetoaddress(6, dummy_address))
    time.sleep(5)

    # There should be no pending channels
    pending_channels = taker.lnd.PendingChannels(
        lnmsg.PendingChannelsRequest()
    ).pending_open_channels
    assert len(pending_channels) == 0

    print(taker.lnd.ListChannels(lnmsg.ListChannelsRequest()))
