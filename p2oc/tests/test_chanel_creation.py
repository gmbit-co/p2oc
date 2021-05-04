import os
import time
import pytest

import click
import bitcoin

from p2oc.offer import Offer, OfferCreator, OfferResponse, OfferValidator
from p2oc.channel import ChannelManager
from p2oc.fund import FundingTx
from p2oc.lnd_rpc import LndRpc, lnmsg
from p2oc.btc_rpc import Proxy, Config


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
def network():
    return "regtest"


@pytest.fixture
def taker(btc_rpc):
    lnd_rpc = LndRpc(
        host="ali-lnd:10009",
        cert_path="/ali-lnd/tls.cert",
        macaroon_path="/ali-lnd/data/chain/bitcoin/regtest/admin.macaroon",
    )

    maker = dict(
        address=lnd_rpc.lnd.NewAddress(
            lnmsg.NewAddressRequest(type=lnmsg.AddressType.WITNESS_PUBKEY_HASH)
        ),
        lnd_rpc=lnd_rpc,
        btc_rpc=btc_rpc,
        offer_validator=OfferValidator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc),
        offer_creator=OfferCreator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc),
        funder=FundingTx(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc),
        channel_manger=ChannelManager(lnd_rpc=lnd_rpc),
    )
    return maker


@pytest.fixture
def maker(btc_rpc):
    lnd_rpc = LndRpc(
        host="bob-lnd:10009",
        cert_path="/bob-lnd/tls.cert",
        macaroon_path="/bob-lnd/data/chain/bitcoin/regtest/admin.macaroon",
    )

    maker = dict(
        address=lnd_rpc.lnd.NewAddress(
            lnmsg.NewAddressRequest(type=lnmsg.AddressType.WITNESS_PUBKEY_HASH)
        ),
        lnd_rpc=lnd_rpc,
        btc_rpc=btc_rpc,
        offer_validator=OfferValidator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc),
        offer_creator=OfferCreator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc),
        funder=FundingTx(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc),
        channel_manger=ChannelManager(lnd_rpc=lnd_rpc),
    )
    return maker


def test_double_funded_channel_open(maker, taker):
    request_fund_amount = 16000000
    premium_amount = 100000

    dummy_address = "bcrt1qt0h92s90wveszpqj0rs6tw400h6dp6as48l2t9"

    # Mine and fund wallets
    _ = list(taker["btc_rpc"].generatetoaddress(400, dummy_address))
    _ = list(taker["btc_rpc"].generatetoaddress(10, maker["address"].address))
    _ = list(taker["btc_rpc"].generatetoaddress(10, taker["address"].address))
    _ = list(taker["btc_rpc"].generatetoaddress(120, dummy_address))

    # Give LNDs time to catch up
    time.sleep(8)

    # T1. Create and send offer
    offer, taker_inputs, taker_key_desc = taker["offer_creator"].create(
        premium_amount=premium_amount, fund_amount=request_fund_amount
    )
    offer_ser = offer.serialize()

    # M1. Validate offer
    offer = Offer.deserialize(offer_ser)
    assert maker["offer_validator"].validate(offer)

    funding_offer, maker_inputs, maker_key_desc = maker["offer_creator"].create(
        premium_amount=offer.premium_amount, fund_amount=offer.fund_amount, fund=True
    )

    # M2. Connect to peer
    connected = maker["channel_manger"].connect_peer(offer.node_pubkey, offer.node_host)
    if not connected:
        click.echo(
            f"Failed to connect to peer at pubkey={offer.node_pubkey} "
            + f"host={offer.node_host}"
        )
        return

    # M3. Create funding transaction
    funding_tx, funding_output_idx = maker["funder"].create(
        maker_pubkey=funding_offer.chan_pubkey,
        taker_pubkey=offer.chan_pubkey,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        maker_inputs=funding_offer.inputs,
        taker_inputs=offer.inputs,
        maker_change_output=funding_offer.change_output,
        taker_change_output=offer.change_output,
    )

    # M4. Register channel shim
    channel_id = maker["channel_manger"].register_shim(
        fund_amount=offer.fund_amount,
        premium_amount=offer.premium_amount,
        local_key_desc=maker_key_desc,
        remote_pubkey=offer.chan_pubkey,
        funding_txid=funding_tx.GetTxid(),
        funding_output_idx=funding_output_idx,
    )

    # M5. Sign and respond
    signed_witness = maker["funder"].signed_witness(
        funding_inputs=maker_inputs,
        funding_tx=funding_tx,
        # for simplicity Bob's input is 0
        input_idx=0,
    )

    offer_response = OfferResponse(
        offer_id=offer.offer_id,
        node_host=funding_offer.node_host,
        node_pubkey=funding_offer.node_pubkey,
        channel_id=channel_id,
        chan_pubkey=maker_key_desc.raw_key_bytes,
        funding_output_idx=funding_output_idx,
        funding_tx=funding_tx,
        signed_witness=signed_witness,
    )

    offer_response = offer_response.serialize()
    offer_response = OfferResponse.deserialize(offer_response)

    # T2. Validate response
    taker["offer_validator"].validate_offer_response(offer, offer_response)

    # T3. Open channel
    taker["channel_manger"].open_pending_channel(
        key_desc=taker_key_desc,
        offer_response=offer_response,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
    )

    # T4. Complete signing and publish
    signed_witness = taker["funder"].signed_witness(
        funding_inputs=taker_inputs,
        funding_tx=offer_response.funding_tx,
        # Assume we are the last one
        input_idx=len(offer_response.funding_tx.vin) - 1,
    )

    final_funding_tx = taker["funder"].create_signed_funding_tx(
        offer_response.funding_tx,
        [offer_response.signed_witness, signed_witness],
    )

    taker["funder"].publish(final_funding_tx)

    # Confirm channel got oppened (send)
    _ = list(taker["btc_rpc"].generatetoaddress(6, dummy_address))
    time.sleep(5)

    # There should be no pending channels
    assert (
        len(
            taker["lnd_rpc"]
            .lnd.PendingChannels(lnmsg.PendingChannelsRequest())
            .pending_open_channels
        )
        == 0
    )

    print(taker["lnd_rpc"].lnd.ListChannels(lnmsg.ListChannelsRequest()))
