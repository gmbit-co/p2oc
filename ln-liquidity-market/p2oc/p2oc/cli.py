import os
import codecs

import click
import bitcoin

from .offer import (
    Offer,
    OfferCreator,
    OfferResponse,
    OfferValidator,
    ChannelManager,
    FundingTx,
)
from .lnd_rpc import LndRpc, lnmsg
from .btc_rpc import Proxy, Config


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--request_fund_amount",
    required=True,
    type=int,
    help="Satoshis to request from liquidity provider",
)
@click.option(
    "--premium_amount",
    required=True,
    type=int,
    help="Satoshis to pay to liquidity provider in exchange for the inbound liquidity.",
)
@click.option(
    "--network", default="regtest", help="Bitcoin network to use (e.g. regtest"
)
def createoffer(request_fund_amount, premium_amount, network):
    lnd_rpc, btc_rpc = _build_rpc_clients(network)

    offer_creator = OfferCreator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    offer, inputs, key_desc = offer_creator.create(
        premium_amount=premium_amount, fund_amount=request_fund_amount
    )
    offer_ser = offer.serialize()
    click.echo(
        "Send the following offer to the party you want to open a channel with:\n"
    )
    click.echo(offer_ser)

    offer_response = click.prompt("\nPaste the offer response for the other party")
    # It's base64, let's encode from str to bytes
    offer_response = offer_response.encode("ascii")
    offer_response = OfferResponse.deserialize(offer_response)

    validator = OfferValidator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    validator.validate_offer_response(offer, offer_response)

    ChannelManager.open_pending_channel(
        lnd_rpc=lnd_rpc,
        key_desc=key_desc,
        offer_response=offer_response,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
    )

    # Combine signatures
    signed_witness = FundingTx.signed_witness(
        funding_inputs=inputs,
        funding_tx=offer_response.funding_tx,
        # Assume we are the last one
        input_idx=len(offer_response.funding_tx.vin) - 1,
        lnd_rpc=lnd_rpc,
    )

    final_funding_tx = FundingTx.create_signed_funding_tx(
        offer_response.funding_tx, [offer_response.signed_witness, signed_witness]
    )

    final_funding_tx_id = btc_rpc.sendrawtransaction(final_funding_tx)

    final_funding_tx_id = codecs.encode(final_funding_tx_id, "hex").decode("ascii")
    click.echo(
        f"Success! The published funding transaction ID is {final_funding_tx_id}"
    )


@cli.command()
@click.argument("offer", required=True)
@click.option(
    "--network", default="regtest", help="Bitcoin network to use (e.g. regtest"
)
def createchannelfromoffer(offer, network):
    """The offer we'll use to create a channel from."""
    lnd_rpc, btc_rpc = _build_rpc_clients(network)

    offer = Offer.deserialize(offer)
    offer_validator = OfferValidator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    assert offer_validator.validate(offer)

    # XXX: Bob pays funding tx fee but he does not have to
    offer_creator = OfferCreator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    funding_offer, inputs, key_desc = offer_creator.create(
        premium_amount=offer.premium_amount, fund_amount=offer.fund_amount, fund=True
    )

    funding_tx_creator = FundingTx()
    funding_tx, funding_output_idx = funding_tx_creator.create(
        maker_pubkey=funding_offer.chan_pubkey,
        taker_pubkey=offer.chan_pubkey,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        maker_inputs=funding_offer.inputs,
        taker_inputs=offer.inputs,
        maker_change_output=funding_offer.change_output,
        taker_change_output=offer.change_output,
    )

    # TODO: Assumes whoever creates offer is accessible
    connect_peer_req = lnmsg.ConnectPeerRequest(
        addr=lnmsg.LightningAddress(
            pubkey=offer.node_pubkey,
            # TODO: Why can't we include the port?
            host=offer.node_host.split(":")[0],
        )
    )

    try:
        lnd_rpc.lnd.ConnectPeer(connect_peer_req)
    except:
        pass

    # Confirm that we are connected
    peers = lnd_rpc.lnd.ListPeers(lnmsg.ListPeersRequest())
    assert len(peers.peers) == 1 and peers.peers[0].pub_key == offer.node_pubkey

    channel_id = ChannelManager.register_shim(
        lnd_rpc=lnd_rpc,
        fund_amount=offer.fund_amount,
        premium_amount=offer.premium_amount,
        local_key_desc=key_desc,
        remote_pubkey=offer.chan_pubkey,
        funding_txid=funding_tx.GetTxid(),
        funding_output_idx=funding_output_idx,
    )

    signed_witness = FundingTx.signed_witness(
        funding_inputs=inputs,
        funding_tx=funding_tx,
        # for simplicity Bob's input is 0
        input_idx=0,
        lnd_rpc=lnd_rpc,
    )

    offer_response = OfferResponse(
        offer_id=offer.offer_id,
        node_host=funding_offer.node_host,
        node_pubkey=funding_offer.node_pubkey,
        channel_id=channel_id,
        chan_pubkey=key_desc.raw_key_bytes,
        funding_output_idx=funding_output_idx,
        funding_tx=funding_tx,
        signed_witness=signed_witness,
    )

    offer_response = offer_response.serialize()

    click.echo(
        "Send the following offer response back to the party you want to open a channel with:\n"
    )
    click.echo(offer_response)


def _build_rpc_clients(network):
    # TODO: Find better approach than envvars for passing inc onfig
    lnd_rpc = LndRpc(
        host=os.environ["LND_ENDPOINT"],
        cert_path=os.environ["LND_CERTPATH"],
        macaroon_path=os.environ["LND_MRNPATH"],
    )

    bitcoin.SelectParams(network)
    btc_rpc = Proxy(
        config=Config(
            rpcuser=os.environ["BTCD_RPCUSER"],
            rpcpassword=os.environ["BTCD_RPCPASS"],
            rpcconnect=os.environ["BTCD_RPCHOST"],
            rpcport=os.environ["BTCD_RPCPORT"],
        )
    )

    return lnd_rpc, btc_rpc
