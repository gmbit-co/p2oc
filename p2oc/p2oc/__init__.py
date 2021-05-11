import os
import sys

# HACK: Workaround for relative import in protobuf under python3
# https://github.com/PaddlePaddle/Paddle/pull/18239
cur_path = os.path.dirname(__file__)
parent_path = os.path.dirname(cur_path)
sys.path.append(os.path.join(parent_path, "lnrpc"))


from bitcointx.core.psbt import PSBT_Output

from p2oc.lnd_rpc import lnmsg
from p2oc import signing as p2oc_signing
from p2oc import address as p2oc_address
from p2oc import funding as p2oc_funding
from p2oc import channel as p2oc_channel
from p2oc import offer as p2oc_offer
from bitcoin.rpc import unhexlify


def create_offer(premium_amount, fund_amount, lnd):
    psbt = p2oc_signing.allocate_funds(premium_amount, lnd, include_tx_fee=True)

    key_desc = p2oc_address.derive_next_multisig_key_desc(lnd)
    node_pubkey = lnd.lnd.GetInfo(lnmsg.GetInfoRequest()).identity_pubkey
    offer = p2oc_offer.Offer(
        # TODO: Find a way to get this internally
        node_host="ali-lnd",
        node_pubkey=node_pubkey,
        premium_amount=premium_amount,
        fund_amount=fund_amount,
        channel_pubkey_key_desc=key_desc,
        input_indices=list(range(len(psbt.unsigned_tx.vin))),
        output_indices=list(range(len(psbt.unsigned_tx.vout))),
    )

    p2oc_offer.attach_offer_to_psbt(offer, psbt, lnd)

    return psbt


def accept_offer(offer_psbt, lnd):
    offer = p2oc_offer.get_offer_from_psbt(offer_psbt)

    p2oc_offer.validate_offer_was_not_tampered(offer_psbt, lnd)
    p2oc_offer.validate_offer_psbt(offer_psbt)

    p2oc_channel.connect_peer(
        node_pubkey=offer.node_pubkey, node_host=offer.node_host, lnd=lnd
    )

    # This is to obtain our UTXOs
    allocated_psbt = p2oc_signing.allocate_funds(
        offer.fund_amount, lnd, include_tx_fee=False
    )
    p2oc_signing.copy_inputs(from_psbt=allocated_psbt, to_psbt=offer_psbt)

    key_desc = p2oc_address.derive_next_multisig_key_desc(lnd)

    funding_output = p2oc_funding.create_funding_output(
        taker_pubkey=offer.channel_pubkey_key_desc.raw_key_bytes,
        maker_pubkey=key_desc.raw_key_bytes,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
    )

    # Add funding output to the original psbt must be the last one
    offer_psbt.add_output(funding_output, PSBT_Output())
    if offer_psbt.get_output_amounts()[-1] != offer.fund_amount + offer.premium_amount:
        raise RuntimeError(
            f"PSBT output amount ({offer_psbt.get_output_amounts()[-1]}) does not add "
            + f"up to fund + premium ({offer.fund_amount + offer.premium_amount})"
        )

    # TODO: Currently both parties pay fees. It makes more sense for only the taker
    #       to pay the fees.

    channel_id = p2oc_channel.generate_channel_id(
        offer.channel_pubkey_key_desc.raw_key_bytes, key_desc.raw_key_bytes
    )

    channel_point_shim = p2oc_channel.create_channel_point_shim(
        channel_id=channel_id,
        unsigned_tx_out=offer_psbt.unsigned_tx,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        local_key_desc=key_desc,
        remote_pubkey=offer.channel_pubkey_key_desc.raw_key_bytes,
    )

    p2oc_channel.register_channel_point_shim(channel_point_shim, lnd)

    input_indices = []
    for i in range(len(offer_psbt.unsigned_tx.vin)):
        if i not in offer.input_indices:
            input_indices.append(i)

    output_indices = []
    for i in range(len(offer_psbt.unsigned_tx.vout) - 1):  # '-1' to exclude funding tx
        if i not in offer.output_indices:
            output_indices.append(i)

    node_pubkey = lnd.lnd.GetInfo(lnmsg.GetInfoRequest()).identity_pubkey
    reply = p2oc_offer.OfferReply(
        # TODO: Find a way to get this internally
        node_host="bob-lnd",
        node_pubkey=node_pubkey,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        channel_id=channel_id,
        channel_pubkey_key_desc=key_desc,
        input_indices=input_indices,
        output_indices=output_indices,
    )

    p2oc_offer.attach_offer_reply_to_psbt(reply, offer_psbt, lnd)

    # Offer PSBT has been modified to now become the reply PSBT
    reply_psbt = offer_psbt
    return reply_psbt


def open_channel(unsigned_psbt, lnd):
    offer = p2oc_offer.get_offer_from_psbt(unsigned_psbt)
    reply = p2oc_offer.get_offer_reply_from_psbt(unsigned_psbt)

    p2oc_offer.validate_offer_was_not_tampered(unsigned_psbt, lnd)
    p2oc_offer.validate_offer_reply_was_not_tampered(unsigned_psbt, lnd)

    # Funding output is the last one
    assert (
        offer.premium_amount + offer.fund_amount
        == unsigned_psbt.get_output_amounts()[-1]
    )

    # TODO: check that our inputs and outputs were included
    channel_point_shim = p2oc_channel.create_channel_point_shim(
        channel_id=reply.channel_id,
        unsigned_tx_out=unsigned_psbt.unsigned_tx,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        local_key_desc=offer.channel_pubkey_key_desc,
        remote_pubkey=reply.channel_pubkey_key_desc.raw_key_bytes,
    )

    p2oc_channel.open_channel(
        node_pubkey=unhexlify(reply.node_pubkey),
        fund_amount=offer.fund_amount,
        premium_amount=offer.premium_amount,
        channel_point_shim=channel_point_shim,
        lnd=lnd,
    )

    # TODO: Check that the channel is pending
    # if lnd.lnd.PendingChannels(lnmsg.PendingChannelsRequest())...

    # At this point we should have commitment transactions signed and we can sign the funding transaction
    # TODO: How can we check with lnd that this is the case?
    p2oc_signing.sign_inputs(
        unsigned_psbt, offer.input_indices, offer.channel_pubkey_key_desc, lnd
    )

    # Unsigned PSBT has been modified to now become the half-signed PSBT
    half_signed_psbt = unsigned_psbt
    return half_signed_psbt


def finalize_offer(half_signed_psbt, lnd):
    offer = p2oc_offer.get_offer_from_psbt(half_signed_psbt)
    reply = p2oc_offer.get_offer_reply_from_psbt(half_signed_psbt)

    p2oc_offer.validate_offer_was_not_tampered(half_signed_psbt, lnd)
    p2oc_offer.validate_offer_reply_was_not_tampered(half_signed_psbt, lnd)

    p2oc_channel.validate_pending_channel_matches_offer(offer, half_signed_psbt, lnd)
    p2oc_signing.sign_inputs(
        half_signed_psbt, reply.input_indices, reply.channel_pubkey_key_desc, lnd
    )
    p2oc_signing.finalize_and_publish_psbt(half_signed_psbt, lnd)


def inspect(psbt):
    return p2oc_offer.deserialize_psbt(psbt)
