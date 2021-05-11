import click

import p2oc
from .lnd_rpc import LndRpc
from .psbt import deserialize_psbt


@click.group()
def cli():
    pass


def lnd_options(function):
    function = click.option("-c", "--configfile", type=str)(function)
    function = click.option("-h", "--host", type=str)(function)
    function = click.option(
        "-n",
        "--network",
        type=click.Choice(
            [
                "mainnet",
                "testnet",
                "simnet",
                "regtest",
            ]
        ),
    )(function)
    function = click.option("--tlscertpath", type=str)(function)
    function = click.option("--adminmacaroonpath", type=str)(function)
    return function


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
@lnd_options
def createoffer(premium, fund, **lnd_options):
    lnd = _lnd_from_options(lnd_options)

    offer_psbt = p2oc.create_offer(premium_amount=premium, fund_amount=fund, lnd=lnd)
    offer_psbt = offer_psbt.to_base64()

    click.echo(
        "\nSend the following offer to the funding peer you want to open a channel with for them to accept:\n"
    )
    click.echo(offer_psbt)


@cli.command()
@click.argument("offer_psbt", required=True)
@lnd_options
def acceptoffer(offer_psbt, **lnd_options):
    lnd = _lnd_from_options(lnd_options)

    offer_psbt = deserialize_psbt(offer_psbt)

    reply_psbt = p2oc.accept_offer(offer_psbt, lnd)
    reply_psbt = reply_psbt.to_base64()

    click.echo(
        "\nSend the following reply back to peer requesting liquidity to indicate you are approving the offer:\n"
    )
    click.echo(reply_psbt)


@cli.command()
@click.argument("unsigned_psbt", required=True)
@lnd_options
def openchannel(unsigned_psbt, **lnd_options):
    lnd = _lnd_from_options(lnd_options)

    unsigned_psbt = deserialize_psbt(unsigned_psbt)

    half_signed_psbt = p2oc.open_channel(unsigned_psbt, lnd)
    half_signed_psbt = half_signed_psbt.to_base64()

    click.echo(
        "\nYou've successfully signed the funding tx and opened a pending channel. "
        + "Send the final reply back to the funder for them to finalize and publish. "
        + "The channel can be used after 6 confirmation.:\n"
    )
    click.echo(half_signed_psbt)


@cli.command()
@click.argument("half_signed_psbt", required=True)
@lnd_options
def finalizeoffer(half_signed_psbt, **lnd_options):
    lnd = _lnd_from_options(lnd_options)

    half_signed_psbt = deserialize_psbt(half_signed_psbt)
    p2oc.finalize_offer(half_signed_psbt, lnd)

    click.echo(
        "\nCongratulations! The channel has been opened and funded. It can be used "
        + "after 6 confirmations."
    )


def _lnd_from_options(options):
    def _without_nones(dict_):
        return {k: v for k, v in dict_.items() if v is not None}

    config_path = options.pop("configfile")
    options = _without_nones(options)
    lnd = LndRpc(config_path=config_path, config_overrides=options)
    return lnd
