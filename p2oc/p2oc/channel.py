import base64
import time
import hashlib

from bitcoin.rpc import unhexlify

from .lnd_rpc import lnmsg


def genchannelid(taker_pubkey, maker_pubkey):
    # something that is unique to the corresponding matched taker and maker
    channel_id = hashlib.sha256(
        (
            base64.b64encode(maker_pubkey + taker_pubkey).decode("ascii")
            + str(time.time())
        ).encode()
    ).hexdigest()
    return channel_id


class ChannelManager:
    def __init__(self, lnd_rpc):
        self._lnd_rpc = lnd_rpc

    def register_shim(
        self,
        fund_amount,
        premium_amount,
        local_key_desc,
        remote_pubkey,
        funding_txid,
        funding_output_idx,
    ):
        local_pubkey = local_key_desc.raw_key_bytes
        channel_id = genchannelid(local_pubkey, remote_pubkey)
        chan_point = lnmsg.ChannelPoint(
            funding_txid_bytes=funding_txid, output_index=funding_output_idx
        )

        # define our key for funding output
        local_key = lnmsg.KeyDescriptor(
            raw_key_bytes=local_key_desc.raw_key_bytes,
            key_loc=lnmsg.KeyLocator(
                key_family=local_key_desc.key_loc.key_family,
                key_index=local_key_desc.key_loc.key_index,
            ),
        )

        chan_point_shim = lnmsg.ChanPointShim(
            amt=fund_amount + premium_amount,
            chan_point=chan_point,
            local_key=local_key,
            remote_key=remote_pubkey,
            pending_chan_id=unhexlify(channel_id),
            thaw_height=0,  # set 0 for simplicity
        )

        ftm = lnmsg.FundingTransitionMsg(
            shim_register=lnmsg.FundingShim(chan_point_shim=chan_point_shim)
        )

        self._lnd_rpc.lnd.FundingStateStep(ftm)
        return channel_id

    def open_pending_channel(
        self, key_desc, offer_response, premium_amount, fund_amount
    ):
        chan_point = lnmsg.ChannelPoint(
            funding_txid_bytes=offer_response.funding_tx.GetTxid(),
            output_index=offer_response.funding_output_idx,
        )

        # our funding key
        local_key = lnmsg.KeyDescriptor(
            raw_key_bytes=key_desc.raw_key_bytes,
            key_loc=lnmsg.KeyLocator(
                key_family=key_desc.key_loc.key_family,
                key_index=key_desc.key_loc.key_index,
            ),
        )

        chan_point_shim = lnmsg.ChanPointShim(
            amt=fund_amount + premium_amount,
            chan_point=chan_point,
            local_key=local_key,
            remote_key=offer_response.chan_pubkey,
            pending_chan_id=unhexlify(offer_response.channel_id),
            thaw_height=0,  # for simplicity
        )

        funding_shim = lnmsg.FundingShim(chan_point_shim=chan_point_shim)

        open_chan_req = lnmsg.OpenChannelRequest(
            node_pubkey=unhexlify(offer_response.node_pubkey),
            local_funding_amount=fund_amount + premium_amount,
            push_sat=fund_amount,  # fund amount is pushed to the remote end (Bob)
            funding_shim=funding_shim,
        )

        chan_event_stream = self._lnd_rpc.lnd.OpenChannel(open_chan_req)
        next(chan_event_stream)

        # Check that the channel is pending
        self._lnd_rpc.lnd.PendingChannels(lnmsg.PendingChannelsRequest())

    def connect_peer(self, node_pubkey, node_host):
        # TODO: Assumes whoever creates offer is accessible
        connect_peer_req = lnmsg.ConnectPeerRequest(
            addr=lnmsg.LightningAddress(
                pubkey=node_pubkey,
                # TODO: Why can't we include the port?
                host=node_host.split(":")[0],
            )
        )

        try:
            self._lnd_rpc.lnd.ConnectPeer(connect_peer_req)
        except:
            # TODO: Only allow an already connected failure
            pass

        # Confirm that we are connected
        peers = self._lnd_rpc.lnd.ListPeers(lnmsg.ListPeersRequest())

        # TODO: Add product-level check
        return len(peers.peers) == 1 and peers.peers[0].pub_key == node_pubkey
