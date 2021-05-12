import textwrap
import collections

import click

import p2oc
from .lnd_rpc import LndRpc
from .psbt import deserialize_psbt
from . import pretty_print as pprint


class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        #: the registered subcommands by their exported names.
        self.commands = commands or collections.OrderedDict()

    def list_commands(self, ctx):
        return self.commands


@click.group(
    cls=OrderedGroup,
    help=f"""
{click.style("p2oc (Pay to Open Channel)", bold=True)} is a protocol atop running
Lightning Network nodes (presently LND - https://github.com/lightningnetwork/lnd) to
allow a node to request an inbound channel of a given size ("fund amount") from another
node in exchange for a fee ("premium amount") which is paid immediately as part of the
funding transaction. The procedure presently involves going back and forth 2x, but will
be made more streamlined in the future.

Under the hood, we are creating a custom funding transaction with multiple inputs by
passing a PSBT back and forth between the two parties to build up this transaction.

~

{click.style("Following is the order of commands to be run and by which party:", bold=True)}

\b
{click.style("Step 1 (run by Taker, requesting inbound channel)", bold=True)}
$ p2oc p2oc createoffer --premium=100000 --fund=1500000
<offer_psbt>

\b
{click.style("Step 2 (run by Maker, providing channel)", bold=True)}
$ p2oc acceptoffer <offer_psbt>
<unsigned_psbt>

\b
{click.style("Step 3 (run by Taker)", bold=True)}
$ p2oc openchannel <unsigned_psbt>
<half_signed_psbt>

\b
{click.style("Step 4 (run by Maker)", bold=True)}
$ p2oc finalizeoffer <half_signed_psbt>""",
)
@click.option(
    "-c",
    "--configfile",
    type=str,
    help="""The path to the LND config file (by default under ~/.lnd/lnd.conf). The
host, network, tlscertpath, and adminmacaroonpath will be looked for in this config
file. If those params are passed manually they will override what was found in the
config file.""",
)
@click.option("-h", "--host", type=str, help="The host of your node.")
@click.option(
    "-n",
    "--network",
    type=click.Choice(["mainnet", "testnet", "simnet", "regtest"]),
    help="The network your lightning node is running on.",
)
@click.option(
    "--tlscertpath",
    type=str,
    help="The path to the LND's tls certificate (by default under ~/.lnd/tls.cert).",
)
@click.option(
    "--adminmacaroonpath",
    type=str,
    help="""The path to the LND's admin macaroon path (by default under
    ~/.lnd/data/chain/bitcoin/testnet/admin.macaroon).""",
)
@click.pass_context
def cli(ctx, **lnd_options):
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called by means
    # other than the `if` block below).
    ctx.ensure_object(dict)
    ctx.obj["lnd_options"] = lnd_options


@cli.command(
    short_help=f"""{click.style("(Step 1)", bold=True)} Create an offer to request an
inbound funded channel (of fund amount) in exchange for a fee (premium amount). You
can send this offer to another node operator for them to accept and provide liquidity."""
)
@click.option(
    "--premium",
    required=True,
    type=int,
    help="Amount in satoshis to pay to liquidity provider in exchange for the "
    + "inbound liquidity.",
)
@click.option(
    "--fund",
    required=True,
    type=int,
    help="Amount in satoshis to request from liquidity provider.",
)
@click.pass_context
def createoffer(ctx, premium, fund):
    pretty_echo_header("Create Offer")

    lnd = _lnd_from_options(ctx.obj["lnd_options"])
    offer_psbt = p2oc.create_offer(premium_amount=premium, fund_amount=fund, lnd=lnd)

    pretty_echo_psbt(offer_psbt, "taker")
    click.confirm(
        "Please confirm if you'd like to create this offer", default=True, abort=True
    )

    click.secho(
        "\nSend the following offer to the funding peer you want to open a channel "
        + "with for them to accept:\n",
        bold=True,
    )

    click.echo(offer_psbt.to_base64())


@cli.command(
    short_help=f"""{click.style("(Step 2)", bold=True)} Accept an offer requesting an
inbound funded channel (of fund amount) of which you'd provide. In exchange you'll
receive an upfront fee (of premium amount)."""
)
@click.argument("offer_psbt", required=True)
@click.pass_context
def acceptoffer(ctx, offer_psbt):
    pretty_echo_header("Accept Offer")

    lnd = _lnd_from_options(ctx.obj["lnd_options"])
    offer_psbt = deserialize_psbt(offer_psbt)

    pretty_echo_psbt(offer_psbt, "maker")
    click.confirm(
        "Please confirm if you'd like to accept this offer", default=True, abort=True
    )

    reply_psbt = p2oc.accept_offer(offer_psbt, lnd)

    pretty_echo_psbt(reply_psbt, "maker")
    click.confirm("Please confirm your reply", default=True, abort=True)

    click.secho(
        "\nSend the following reply back to peer requesting liquidity to indicate "
        + "you have approved the offer:\n",
        bold=True,
    )

    click.echo(reply_psbt.to_base64())


@cli.command(
    short_help=f"""{click.style("(Step 3)", bold=True)} With an accepted offer in-hand,
create and open the channel. It will be in pending state after this command."""
)
@click.argument("unsigned_psbt", required=True)
@click.pass_context
def openchannel(ctx, unsigned_psbt):
    pretty_echo_header("Open Channel")

    lnd = _lnd_from_options(ctx.obj["lnd_options"])
    unsigned_psbt = deserialize_psbt(unsigned_psbt)

    pretty_echo_psbt(unsigned_psbt, "taker")
    click.confirm(
        "Please confirm if you'd like to proceed in opening the channel",
        default=True,
        abort=True,
    )

    half_signed_psbt = p2oc.open_channel(unsigned_psbt, lnd)
    half_signed_psbt = half_signed_psbt.to_base64()

    click.secho(
        "\nYou've successfully signed the funding tx and opened a pending channel. "
        + "Send the final reply back to the funder for them to finalize and publish. "
        + "The channel can be used after 6 confirmation.:\n",
        bold=True,
    )

    click.echo(half_signed_psbt)


@cli.command(
    short_help=f"""{click.style("(Step 4)", bold=True)} Finalize the p2oc procedure by
publishing the funding transaction. This channel can begin to be used after 6
confirmations."""
)
@click.argument("half_signed_psbt", required=True)
@click.pass_context
def finalizeoffer(ctx, half_signed_psbt):
    pretty_echo_header("Finalize Offer")

    lnd = _lnd_from_options(ctx.obj["lnd_options"])
    half_signed_psbt = deserialize_psbt(half_signed_psbt)

    pretty_echo_psbt(half_signed_psbt, "maker")
    click.confirm(
        "Please confirm to publish the funding tx and complete channel opening",
        default=True,
        abort=True,
    )

    p2oc.finalize_offer(half_signed_psbt, lnd)

    click.secho(
        "\nCongratulations! The channel has been opened and funded. It can be used "
        + "after 6 confirmations.\n",
        bold=True,
    )


@cli.command(
    short_help="""Inspect the p2oc payload at anytime to see the details of the PSBT
being passed back and forth."""
)
@click.argument("psbt", required=True)
def inspect(psbt):
    psbt = deserialize_psbt(psbt)
    offer = p2oc.offer.get_offer_from_psbt(psbt, raise_if_missing=False)
    reply = p2oc.offer.get_offer_reply_from_psbt(psbt, raise_if_missing=False)

    click.echo()
    click.secho("Inspect PSBT\n", bold=True, underline=True)
    click.secho("psbt.inputs:", bold=True)
    click.echo(textwrap.indent(pprint.pretty_psbt_inputs(psbt.inputs), "  "))
    click.secho("psbt.outputs:", bold=True)
    click.echo(textwrap.indent(pprint.pretty_outputs(psbt.outputs), "  "))
    click.secho("psbt.unsigned_tx:", bold=True)
    click.echo(textwrap.indent(pprint.pretty_tx(psbt.unsigned_tx), "  "))

    click.secho("Inspect Offer\n", bold=True, underline=True)
    if offer is not None:
        click.echo(pprint.pretty_offer(offer))
    else:
        click.echo("N/A")

    click.secho("Inspect Reply\n", bold=True, underline=True)
    if reply is not None:
        click.echo(pprint.pretty_reply(reply))
    else:
        click.echo("N/A")


def _lnd_from_options(options):
    def _without_nones(dict_):
        return {k: v for k, v in dict_.items() if v is not None}

    config_path = options.pop("configfile")
    options = _without_nones(options)
    lnd = LndRpc(config_path=config_path, config_overrides=options)
    return lnd


def pretty_echo_psbt(psbt, side):
    offer = p2oc.offer.get_offer_from_psbt(psbt, raise_if_missing=False)
    reply = p2oc.offer.get_offer_reply_from_psbt(psbt, raise_if_missing=False)

    message = ""
    if side == "taker" and offer is not None:
        message = f"""
- You're paying {click.style("{:,}".format(offer.premium_amount), fg="red", bold=True)} SATS premium
- In exchange for a funded channel of {click.style("{:,}".format(offer.fund_amount), fg="green", bold=True)} SATS
- To {click.style(f"{offer.node_pubkey}@{offer.node_host}", bold=True)} (your node)
"""

    if side == "taker" and reply is not None:
        message += f"- From {click.style(f'{reply.node_pubkey}@{reply.node_host}', bold=True)} (their node)"

    if side == "maker" and offer is not None:
        message = f"""
- You're receiving {click.style("{:,}".format(offer.premium_amount), fg="green", bold=True)} SATS
- In exchange for your funded channel of {click.style("{:,}".format(offer.fund_amount), fg="red", bold=True)} SATS
- To {click.style(f"{offer.node_pubkey}@{offer.node_host}", bold=True)} (their node)
"""

    if side == "maker" and reply is not None:
        message += f"- From {click.style(f'{reply.node_pubkey}@{reply.node_host}', bold=True)} (your node)"

    click.echo(message)


def pretty_echo_header(step):
    click.echo()  # newline
    click.secho("┌────────────────────────────┐", bold=True)
    click.secho("│ p2oc (Pay to Open Channel) │", bold=True)
    click.secho("└────────────────────────────┘", bold=True)
    click.echo("\nStep: " + click.style(step, underline=True))
