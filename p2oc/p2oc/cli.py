import os

import click
import bitcoin
import bitcointx.core as bc

from .lnd_rpc import LndRpc
from .btc_rpc import Proxy, Config
from .offer import deserialize_psbt
from . import interface as p2oc


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--premium",
    required=True,
    type=int,
    help="Satoshis to pay to liquidity provider in exchange for the inbound liquidity.",
)
@click.option(
    "--fund",
    required=True,
    type=int,
    help="Satoshis to request from liquidity provider",
)
def createoffer(premium, fund):
    lnd = ...
    # Taker needs to pay premium to open channel
    offer_psbt = p2oc.create_offer(
        # Premium the Taker is willing to pay
        premium_amount=int(premium * bc.CoreCoinParams.COIN),
        # The requested inbound capacity (from Maker)
        fund_offer=int(fund * bc.CoreCoinParams.COIN),
        lnd=lnd,
    )

    offer_psbt = offer_psbt.to_base64()
    print(offer_psbt)


@cli.command()
@click.argument("offer_psbt", required=True)
def acceptoffer(offer_psbt):
    lnd = ...
    offer_psbt = deserialize_psbt(offer_psbt)

    reply_psbt = p2oc.accept_offer(offer_psbt, lnd)
    reply_psbt = reply_psbt.to_base64()
    print(reply_psbt)


@cli.command()
@click.argument("unsigned_psbt", required=True)
def openchannel(unsigned_psbt):
    lnd = ...
    unsigned_psbt = deserialize_psbt(unsigned_psbt)

    half_signed_psbt = p2oc.open_channel(unsigned_psbt, lnd)
    half_signed_psbt = half_signed_psbt.to_base64()
    print(half_signed_psbt)


@cli.command()
@click.argument("half_signed_psbt", required=True)
def finalizeoffer(half_signed_psbt):
    lnd = ...
    half_signed_psbt = deserialize_psbt(half_signed_psbt)
    p2oc.finalize_offer(half_signed_psbt, lnd)


@cli.command()
@click.argument("psbt", required=True)
def inspect(psbt):
    lnd = ...
    decoded = p2oc.inspect(psbt, lnd)
    print(decoded)


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
