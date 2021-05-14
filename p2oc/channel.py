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
            host=node_host,
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


def get_pending_channel(channel_point, lnd):
    # returns pending channel object for given `channel_point` in the format of "tx_id:vout_id"
    # if a channel is not found, raises error
    resp = lnd.lnd.PendingChannels(lnmsg.PendingChannelsRequest())
    if not resp.pending_open_channels:
        raise RuntimeError("No pending channels")

    for pending_chan in resp.pending_open_channels:
        if pending_chan.channel.channel_point == channel_point:
            return pending_chan

    raise RuntimeError(
        f"Unable to find created pending channel for channel point={channel_point}"
    )
