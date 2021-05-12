import pprint
import textwrap

from bitcoin.rpc import hexlify


# TODO: Will likely want to move this into helper functions and just call into
#       them within the CLI.
def pretty_tx(tx):
    NL = "\n"
    return f"""nVersion: {tx.nVersion}
nLockTime: {tx.nLockTime}
vin:
{textwrap.indent(("  " + NL).join(map(str, tx.vin)), "  ")}
vout:
{textwrap.indent(("  " + NL).join(map(str, tx.vout)), "  ")}
wit:
{textwrap.indent(("  " + NL).join(map(str, tx.wit.vtxinwit)), "  ")}"""


def pretty_psbt_inputs(inputs):
    NL = "\n"
    indices = [inp.index for inp in inputs]
    inputs = [
        f"""utxo:
{textwrap.indent(pretty_tx(inp.utxo), "  ")}
redeem_script: {inp.redeem_script}
witness_script: {inp.witness_script}
derivation_map:
{textwrap.indent(pprint.pformat(dict(inp.derivation_map)), "  ")}
final_script_sig: {inp.final_script_sig}
final_script_witness: {inp.final_script_witness}"""
        for inp in inputs
    ]
    inputs = [
        f"{n}:{NL}{textwrap.indent(inp, '  ')}" for n, inp in zip(indices, inputs)
    ]
    return NL.join(inputs)


def pretty_outputs(outputs):
    NL = "\n"
    indices = [out.index for out in outputs]
    outputs = [
        f"""redeem_script: {out.redeem_script}
witness_script: {out.witness_script}
derivation_map:
{textwrap.indent(pprint.pformat(dict(out.derivation_map)), "  ")}"""
        for out in outputs
    ]
    outputs = [
        f"{n}:{NL}{textwrap.indent(out, '  ')}" for n, out in zip(indices, outputs)
    ]
    return NL.join(outputs)


def pretty_offer(offer):
    key_desc = offer.channel_pubkey_key_desc
    return f"""node_host: {offer.node_host}
node_pubkey: {offer.node_pubkey}
premium_amount: {offer.premium_amount}
fund_amount: {offer.fund_amount}
channel_pubkey_key: {hexlify(key_desc.raw_key_bytes)} key_family={key_desc.key_family}, key_index={key_desc.key_index}
"""


def pretty_reply(reply):
    key_desc = reply.channel_pubkey_key_desc
    return f"""node_host: {reply.node_host}
node_pubkey: {reply.node_pubkey}
premium_amount: {reply.premium_amount}
fund_amount: {reply.fund_amount}
channel_pubkey_key: {hexlify(key_desc.raw_key_bytes)} key_family={key_desc.key_family}, key_index={key_desc.key_index}
channel_id: {reply.channel_id}
"""
