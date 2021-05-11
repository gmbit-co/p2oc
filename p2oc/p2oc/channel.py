import time
import base64
import hashlib

import bitcointx.core as bc
from bitcoin.rpc import unhexlify

from .lnd_rpc import lnmsg


def connect_peer(node_pubkey, node_host, lnd):
    connect_peer_req = lnmsg.ConnectPeerRequest(
        addr=lnmsg.LightningAddress(
            pubkey=node_pubkey,
            # TODO: Why can't we include the port?
            host=node_host.split(":")[0],
        )
    )

    try:
        lnd.lnd.ConnectPeer(connect_peer_req)
    except Exception as e:
        if "already connected to peer" not in e.details():
            raise

    # Confirm that we are connected
    peers = lnd.lnd.ListPeers(lnmsg.ListPeersRequest())

    connected = any([peer.pub_key == node_pubkey for peer in peers.peers])
    if not connected:
        raise RuntimeError(f"Unable to connect to peer {node_pubkey}@{node_host}")


def generate_channel_id(taker_pubkey, maker_pubkey):
    # Something that is unique to the corresponding matched taker and maker
    pubkeys = base64.b64encode(taker_pubkey + maker_pubkey).decode("ascii")
    channel_id = hashlib.sha256((pubkeys + str(time.time())).encode()).hexdigest()
    return channel_id


def create_channel_point_shim(
    channel_id,
    unsigned_tx_out,
    premium_amount,
    fund_amount,
    local_key_desc,
    remote_pubkey,
):
    # TODO: Add additional check in this function so it's safe to assume last output
    funding_output_idx = len(unsigned_tx_out.vout) - 1
    funding_txid = unsigned_tx_out.GetTxid()

    channel_point = lnmsg.ChannelPoint(
        funding_txid_bytes=funding_txid, output_index=funding_output_idx
    )

    channel_point_shim = lnmsg.ChanPointShim(
        amt=fund_amount + premium_amount,
        chan_point=channel_point,
        local_key=local_key_desc.to_pb(),
        remote_key=remote_pubkey,
        pending_chan_id=unhexlify(channel_id),
        # TODO: Revisit that this is the appropriate value
        thaw_height=0,  # set 0 for simplicity
    )

    return channel_point_shim


def register_channel_point_shim(shim, lnd):
    msg = lnmsg.FundingTransitionMsg(
        shim_register=lnmsg.FundingShim(chan_point_shim=shim)
    )

    lnd.lnd.FundingStateStep(msg)


def open_channel(
    node_pubkey, fund_amount, premium_amount, channel_point_shim, lnd, confirmations=6
):
    open_chan_req = lnmsg.OpenChannelRequest(
        # TODO: Ensure consistency on where unhexlification is done (i.e. within
        #       functions or outside).
        node_pubkey=node_pubkey,
        local_funding_amount=fund_amount + premium_amount,
        push_sat=fund_amount,
        target_conf=confirmations,
        funding_shim=lnmsg.FundingShim(chan_point_shim=channel_point_shim),
    )

    chan_event_stream = lnd.lnd.OpenChannel(open_chan_req)
    next(chan_event_stream)


def validate_pending_channel_matches_offer(offer, psbt, lnd):
    # check that the channel is pending
    resp = lnd.lnd.PendingChannels(lnmsg.PendingChannelsRequest())
    if not resp.pending_open_channels:
        raise RuntimeError("No pending channels")

    channel_point = (
        f"{bc.b2lx(psbt.unsigned_tx.GetTxid())}:{len(psbt.unsigned_tx.vout)-1}"
    )

    target_channel = None
    for pending_chan in resp.pending_open_channels:
        if pending_chan.channel.channel_point == channel_point:
            target_channel = pending_chan
            break

    if target_channel is None:
        raise RuntimeError(
            f"Unable to find created pending channel for channel point={channel_point}"
        )

    if target_channel.channel.local_balance != offer.fund_amount:
        raise RuntimeError(
            f"Pending channel's local balance={target_channel.channel.local_balance} does not "
            + f"match offer funding amount={offer.fund_amount}"
        )

    # the other party is paying all commitment tx fees
    if target_channel.channel.remote_balance != offer.premium_amount - target_channel.commit_fee:
        raise RuntimeError(
            f"Pending channel's remote balance={target_channel.channel.remote_balance} does not "
            + f"match offer premium amount={offer.premium_amount} minus commit_fee={target_channel.commit_fee}"
        )

    if target_channel.channel.remote_node_pub != offer.node_pubkey:
        raise RuntimeError(
            f"Pending channel's remote node pubkey={target_channel.channel.remote_node_pub} "
            + f"does not match offer's node pubkey={offer.node_pubkey}"
        )
