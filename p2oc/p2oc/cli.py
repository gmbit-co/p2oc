import os
import codecs

import click
import bitcoin

from .offer import Offer, OfferCreator, OfferResponse, OfferValidator
from .channel import ChannelManager
from .fund import FundingTx
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
    offer_validator = OfferValidator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    channel_manger = ChannelManager(lnd_rpc=lnd_rpc)
    funder = FundingTx(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)

    # 1. Create and send offer
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

    # 2. Validate response
    offer_validator.validate_offer_response(offer, offer_response)

    # 3. Open channel
    channel_manger.open_pending_channel(
        key_desc=key_desc,
        offer_response=offer_response,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
    )

    # 4. Complete signing
    signed_witness = funder.signed_witness(
        funding_inputs=inputs,
        funding_tx=offer_response.funding_tx,
        # Assume we are the last one
        input_idx=len(offer_response.funding_tx.vin) - 1,
    )

    final_funding_tx = funder.create_signed_funding_tx(
        offer_response.funding_tx,
        [offer_response.signed_witness, signed_witness],
    )

    # 5. Publish
    final_funding_tx_id = funder.publish(final_funding_tx)
    final_funding_tx_id = codecs.encode(final_funding_tx.GetTxid(), "hex").decode(
        "ascii"
    )
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

    offer_validator = OfferValidator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    offer_creator = OfferCreator(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    funder = FundingTx(lnd_rpc=lnd_rpc, btc_rpc=btc_rpc)
    channel_manger = ChannelManager(lnd_rpc=lnd_rpc)

    # 1. Validate offer
    offer = Offer.deserialize(offer)
    assert offer_validator.validate(offer)

    # XXX: Bob pays funding tx fee but he does not have to
    funding_offer, inputs, key_desc = offer_creator.create(
        premium_amount=offer.premium_amount, fund_amount=offer.fund_amount, fund=True
    )

    # 2. Connect to peer
    connected = channel_manger.connect_peer(offer.node_pubkey, offer.node_host)
    if not connected:
        click.echo(
            f"Failed to connect to peer at pubkey={offer.node_pubkey} "
            + f"host={offer.node_host}"
        )
        return

    # 3. Create funding transaction
    funding_tx, funding_output_idx = funder.create(
        maker_pubkey=funding_offer.chan_pubkey,
        taker_pubkey=offer.chan_pubkey,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        maker_inputs=funding_offer.inputs,
        taker_inputs=offer.inputs,
        maker_change_output=funding_offer.change_output,
        taker_change_output=offer.change_output,
    )

    # 4. Register channel shim
    channel_id = channel_manger.register_shim(
        fund_amount=offer.fund_amount,
        premium_amount=offer.premium_amount,
        local_key_desc=key_desc,
        remote_pubkey=offer.chan_pubkey,
        funding_txid=funding_tx.GetTxid(),
        funding_output_idx=funding_output_idx,
    )

    # 5. Sign and respond
    signed_witness = funder.signed_witness(
        funding_inputs=inputs,
        funding_tx=funding_tx,
        # for simplicity Bob's input is 0
        input_idx=0,
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
        f"""Send the following offer response back to the party you want to open a channel with:

{offer_response.decode('ascii')}
"""
    )


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
