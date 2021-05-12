import os
import sys

# HACK: Workaround for relative import in protobuf under python3
# https://github.com/PaddlePaddle/Paddle/pull/18239
cur_path = os.path.dirname(__file__)
parent_path = os.path.dirname(cur_path)
sys.path.append(os.path.join(parent_path, "lnrpc"))


from bitcointx.core.psbt import PSBT_Output
import bitcointx.core as bc

from p2oc.lnd_rpc import lnmsg
from p2oc import sign as p2oc_sign
from p2oc import address as p2oc_address
from p2oc import fund as p2oc_fund
from p2oc import channel as p2oc_channel
from p2oc import wallet as p2oc_wallet
from p2oc import offer as p2oc_offer
from p2oc import psbt as p2oc_psbt
from bitcoin.rpc import unhexlify


def create_offer(premium_amount, fund_amount, lnd):
    psbt = p2oc_wallet.allocate_funds(premium_amount, lnd, include_tx_fee=True)

    key_desc = p2oc_address.derive_next_multisig_key_desc(lnd)
    node_pubkey = lnd.lnd.GetInfo(lnmsg.GetInfoRequest()).identity_pubkey
    offer = p2oc_offer.Offer(
        state=p2oc_offer.Offer.CREATED_STATE,
        node_host=lnd.host,
        node_pubkey=node_pubkey,
        premium_amount=premium_amount,
        fund_amount=fund_amount,
        channel_pubkey_key_desc=key_desc,
        input_indices=list(range(len(psbt.unsigned_tx.vin))),
        output_indices=list(range(len(psbt.unsigned_tx.vout))),
        input_output_hash=bc.Hash160(psbt.unsigned_tx.serialize()),
    )

    p2oc_offer.attach_offer_to_psbt(offer, psbt, lnd)

    return psbt


def accept_offer(offer_psbt, lnd):
    offer = p2oc_offer.get_offer_from_psbt(offer_psbt)
    p2oc_offer.validate_offer_integrity(offer_psbt, lnd, check_our_signature=False)

    if offer.state != offer.CREATED_STATE:
        raise RuntimeError(
            f"Got offer in a wrong state. Expected state='{offer.CREATED_STATE}'"
            + f", got '{offer.state}'"
        )

    # check that funding UTXOs has not been spent
    # note we can't use `lnd.GetTransactions` since it only knows about our wallet's transactions
    # it's probably safe to skip this step because blockchain will prevent from double spending
    #
    # for vin in offer_psbt.unsigned_tx.vin:
    #     utxo = brpc.gettxout(vin.prevout)
    #     assert utxo is not None
    #

    # TODO: do proper check that there are enough fees for the funding tx
    fees_amount = offer_psbt.get_fee() - offer.premium_amount
    if fees_amount <= 0:
        raise RuntimeError(
            f"Offer PSBT does not incorporate sufficient fees (fees={fees_amount})"
        )

    p2oc_channel.connect_peer(
        node_pubkey=offer.node_pubkey, node_host=offer.node_host, lnd=lnd
    )

    # This is to obtain our UTXOs
    allocated_psbt = p2oc_wallet.allocate_funds(
        offer.fund_amount, lnd, include_tx_fee=False
    )
    p2oc_psbt.merge_psbts(from_psbt=allocated_psbt, to_psbt=offer_psbt)

    key_desc = p2oc_address.derive_next_multisig_key_desc(lnd)

    funding_output = p2oc_fund.create_funding_output(
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
        state=p2oc_offer.OfferReply.ACCEPTED_STATE,
        node_host=lnd.host,
        node_pubkey=node_pubkey,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
        channel_id=channel_id,
        channel_pubkey_key_desc=key_desc,
        input_indices=input_indices,
        output_indices=output_indices,
        input_output_hash=bc.Hash160(allocated_psbt.unsigned_tx.serialize()),
    )

    p2oc_offer.attach_offer_reply_to_psbt(reply, offer_psbt, lnd)

    # Offer PSBT has been modified to now become the reply PSBT
    reply_psbt = offer_psbt
    return reply_psbt


def open_channel(unsigned_psbt, lnd):
    offer = p2oc_offer.get_offer_from_psbt(unsigned_psbt)
    reply = p2oc_offer.get_offer_reply_from_psbt(unsigned_psbt)

    # this should also check that our inputs and outputs were included
    p2oc_offer.validate_offer_integrity(unsigned_psbt, lnd, check_our_signature=True)
    p2oc_offer.validate_offer_reply_integrity(
        unsigned_psbt, lnd, check_our_signature=False
    )

    if offer.state != offer.CREATED_STATE:
        raise RuntimeError(
            f"Got offer in a wrong state. Expected state='{offer.CREATED_STATE}'"
            + f", got '{offer.state}'"
        )

    if reply.state != reply.ACCEPTED_STATE:
        raise RuntimeError(
            f"Got reply in a wrong state. Expected state='{reply.ACCEPTED_STATE}'"
            + f", got '{reply.state}'"
        )

    # check that the funding output is correct
    funding_output = p2oc_fund.create_funding_output(
        taker_pubkey=offer.channel_pubkey_key_desc.raw_key_bytes,
        maker_pubkey=reply.channel_pubkey_key_desc.raw_key_bytes,
        premium_amount=offer.premium_amount,
        fund_amount=offer.fund_amount,
    )

    if unsigned_psbt.unsigned_tx.vout[-1] != funding_output:
        raise RuntimeError(
            "Channel funding does not match parameters between offer and reply"
            + f"Expected funding_output={funding_output}, got {unsigned_psbt.unsigned_tx.vout[-1]}"
        )

    # first, we try to sign the funding tx. In case it fails, we will abort early
    # and not leave pending channel open
    p2oc_sign.sign_inputs(unsigned_psbt, offer.input_indices, lnd)

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

    # Check that the channel is pending
    channel_point = f"{bc.b2lx(unsigned_psbt.unsigned_tx.GetTxid())}:{len(unsigned_psbt.unsigned_tx.vout)-1}"
    _ = p2oc_channel.get_pending_channel(channel_point, lnd)

    # Unsigned PSBT has been modified to now become the half-signed PSBT
    half_signed_psbt = unsigned_psbt

    # update state and re-sign offer
    offer_dict = offer.__dict__.copy()
    offer_dict["state"] = offer.CHANNEL_OPENED_STATE
    offer = p2oc_offer.Offer(**offer_dict)
    p2oc_offer.attach_offer_to_psbt(offer, half_signed_psbt, lnd)
    return half_signed_psbt


def finalize_offer(half_signed_psbt, lnd):
    offer = p2oc_offer.get_offer_from_psbt(half_signed_psbt)
    reply = p2oc_offer.get_offer_reply_from_psbt(half_signed_psbt)

    p2oc_offer.validate_offer_integrity(
        half_signed_psbt, lnd, check_our_signature=False
    )
    p2oc_offer.validate_offer_reply_integrity(
        half_signed_psbt, lnd, check_our_signature=True
    )

    if offer.state != offer.CHANNEL_OPENED_STATE:
        raise RuntimeError(
            f"Got offer in a wrong state. Expected state='{offer.CHANNEL_OPENED_STATE}'"
            + f", got '{offer.state}'"
        )

    if reply.state != reply.ACCEPTED_STATE:
        raise RuntimeError(
            f"Got reply in a wrong state. Expected state='{reply.ACCEPTED_STATE}'"
            + f", got '{reply.state}'"
        )

    # check that the funding output is correct
    funding_output = p2oc_fund.create_funding_output(
        taker_pubkey=offer.channel_pubkey_key_desc.raw_key_bytes,
        maker_pubkey=reply.channel_pubkey_key_desc.raw_key_bytes,
        premium_amount=reply.premium_amount,
        fund_amount=reply.fund_amount,
    )

    if half_signed_psbt.unsigned_tx.vout[-1] != funding_output:
        raise RuntimeError(
            "Channel funding does not match parameters between offer and reply"
            + f"Expected funding_output={funding_output}, got {half_signed_psbt.unsigned_tx.vout[-1]}"
        )

    # check that the channel is pending and has the right config
    channel_point = f"{bc.b2lx(half_signed_psbt.unsigned_tx.GetTxid())}:{len(half_signed_psbt.unsigned_tx.vout)-1}"

    target_channel = p2oc_channel.get_pending_channel(channel_point, lnd)
    if target_channel.channel.local_balance != reply.fund_amount:
        raise RuntimeError(
            f"Pending channel's local balance={target_channel.channel.local_balance} does not "
            + f"match offer funding amount={reply.fund_amount}"
        )

    # the other party is paying all commitment tx fees
    if (
        target_channel.channel.remote_balance
        != reply.premium_amount - target_channel.commit_fee
    ):
        raise RuntimeError(
            f"Pending channel's remote balance={target_channel.channel.remote_balance} does not "
            + f"match offer premium amount={reply.premium_amount} minus commit_fee={target_channel.commit_fee}"
        )

    if target_channel.channel.remote_node_pub != offer.node_pubkey:
        raise RuntimeError(
            f"Pending channel's remote node pubkey={target_channel.channel.remote_node_pub} "
            + f"does not match offer's node pubkey={offer.node_pubkey}"
        )

    p2oc_sign.sign_inputs(half_signed_psbt, reply.input_indices, lnd)
    p2oc_psbt.finalize_and_publish_psbt(half_signed_psbt, lnd)


def inspect(psbt):
    return p2oc_psbt.deserialize_psbt(psbt)
