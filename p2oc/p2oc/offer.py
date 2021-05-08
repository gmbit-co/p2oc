import json
import base64
from dataclasses import dataclass
from typing import Sequence

from bitcointx.core.psbt import PSBT_ProprietaryTypeData


@dataclass(frozen=True)
class Offer:
    # The offer creator's node host and pubkey
    node_host: str
    node_pubkey: str
    premium_amount: float
    fund_amount: float
    # Positions into the PSBT inputs metadata list
    input_indices: Sequence[int]
    output_indices: Sequence[int]
    channel_pubkey: bytes

    def serialize(self):
        offer = json.dumps(self.__dict__).encode()
        return base64.b64encode(offer)

    @classmethod
    def deserialize(cls, offer):
        offer = base64.b64decode(offer)
        offer = json.loads(offer)
        offer = Offer(**offer)
        return offer

    def sign(key_desc):
        """Sign the offer with the given key returning a signed digest (signature)."""
        pass


def attach_offer_to_psbt(offer, psbt):
    """Serializes the offer and attaches it to the proprietary fields of the PSBT in
    place.
    """
    psbt.proprietary_fields[b"offer"] = [
        PSBT_ProprietaryTypeData(0, b"params", offer.serialize()),
        # TODO: Add signature
        PSBT_ProprietaryTypeData(0, b"signature", b"..."),
    ]


"""
import io
import base64
import hashlib
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import List

import bitcoin.core as bc
import bitcoin.core.script as bs
import bitcoin.wallet as bw
from bitcoin.rpc import unhexlify

from .lnd_rpc import LndRpc, lnmsg, walletmsg
from .btc_rpc import Proxy


# XXX: The bitcoinlib CTxWitness deserialization API lacks a classmethod
#      implementation, so we work around by instantiating with dummy data.
def _deserialize_witness(witness, num_witnesses, allow_padding=False):
    fd = io.BytesIO(witness)
    r = bc.CTxWitness(vtxinwit=[0] * num_witnesses).stream_deserialize(fd)
    if not allow_padding:
        padding = fd.read()
        if len(padding) != 0:
            raise bc.serialize.DeserializationExtraDataError(
                "Not all bytes consumed during deserialization", r, padding
            )
    return r


class OfferType(Enum):
    InboundLiquidity = 0


@dataclass(frozen=True)
class Offer:
    offer_id: str
    offer_type: OfferType
    # The offer creator's node host and pubkey
    node_host: str
    node_pubkey: str
    premium_amount: float
    fund_amount: float
    inputs: List[bc.CTxIn]
    change_output: bc.CTxOut
    chan_pubkey: bytes

    def serialize(self):
        offer = self.__dict__.copy()
        b64e = base64.b64encode
        offer["inputs"] = [
            b64e(inp.serialize()).decode("ascii") for inp in offer["inputs"]
        ]
        offer["offer_type"] = offer["offer_type"].value
        offer["change_output"] = b64e(offer["change_output"].serialize()).decode(
            "ascii"
        )
        offer["chan_pubkey"] = b64e(offer["chan_pubkey"]).decode("ascii")
        offer = b64e(json.dumps(offer).encode())
        return offer

    @classmethod
    def deserialize(cls, offer):
        b64d = base64.b64decode
        offer = json.loads(b64d(offer))
        offer["offer_type"] = OfferType(offer["offer_type"])
        offer["inputs"] = [bc.CTxIn.deserialize(b64d(inp)) for inp in offer["inputs"]]
        offer["change_output"] = bc.CTxOut.deserialize(b64d(offer["change_output"]))
        offer["chan_pubkey"] = b64d(offer["chan_pubkey"])
        return Offer(**offer)


@dataclass(frozen=True)
class OfferResponse:
    offer_id: str
    # The offer response creator's node host and pubkey
    node_host: str
    node_pubkey: str
    chan_pubkey: bytes
    channel_id: str
    funding_output_idx: int
    funding_tx: bc.CTransaction
    signed_witness: bc.CTxWitness

    def serialize(self):
        resp = self.__dict__.copy()
        b64e = base64.b64encode
        resp["chan_pubkey"] = b64e(resp["chan_pubkey"]).decode("ascii")
        resp["funding_tx"] = b64e(resp["funding_tx"].serialize()).decode("ascii")
        resp["signed_witness"] = b64e(resp["signed_witness"].serialize()).decode(
            "ascii"
        )
        resp = b64e(json.dumps(resp).encode())
        return resp

    @classmethod
    def deserialize(cls, resp):
        b64d = base64.b64decode
        resp = json.loads(b64d(resp))
        resp["chan_pubkey"] = b64d(resp["chan_pubkey"])
        resp["funding_tx"] = bc.CTransaction.deserialize(b64d(resp["funding_tx"]))
        # XXX: num_witnesses=1 assumption will not be true as we support batch transactions
        resp["signed_witness"] = _deserialize_witness(
            b64d(resp["signed_witness"]), num_witnesses=1
        )
        return OfferResponse(**resp)


def genpubkey(wallet):
    key_family = 0  # multisig?
    key_req = walletmsg.KeyReq(key_family=key_family)
    key_desc = wallet.DeriveNextKey(key_req)
    key_desc = wallet.DeriveNextKey(key_req)  # need to call twice?
    return key_desc


class OfferCreator:
    # TODO: Remove dependency on bitcoin rpc
    def __init__(self, lnd_rpc: LndRpc, btc_rpc: Proxy):
        self._lnd_rpc = lnd_rpc
        self._brpc = btc_rpc

    def create(self, premium_amount, fund_amount, fund=False) -> Offer:
        dummy_psbt, dummy_psbt_decoded = self._dummy_psbt(
            premium_amount, fund_amount, fund
        )

        inputs = []
        for vin in dummy_psbt_decoded["tx"]["vin"]:
            txin = bc.CTxIn(bc.COutPoint(bc.lx(vin["txid"]), vin["vout"]))
            inputs.append(txin)

        # assume there are only 2 outputs: change and channel funding
        assert len(dummy_psbt_decoded["tx"]["vout"]) == 2

        change_output = dummy_psbt_decoded["tx"]["vout"][dummy_psbt.change_output_index]
        change_output = bc.CTxOut(
            int(change_output["value"] * bc.COIN),
            bc.CScript(unhexlify(change_output["scriptPubKey"]["hex"])),
        )

        offer_id = hashlib.sha256(str(time.time()).encode()).hexdigest()
        identity_pubkey = self._lnd_rpc.lnd.GetInfo(
            lnmsg.GetInfoRequest()
        ).identity_pubkey
        pubkey = genpubkey(self._lnd_rpc.wallet)

        offer = Offer(
            # Some random id to match offers and replies
            offer_id=offer_id,
            offer_type=OfferType.InboundLiquidity,
            node_host=self._lnd_rpc.host,
            node_pubkey=identity_pubkey,
            premium_amount=premium_amount,
            fund_amount=fund_amount,
            inputs=inputs,
            change_output=change_output,
            # TODO: How is this pubkey different than the one above?
            chan_pubkey=pubkey.raw_key_bytes,
        )

        # TODO: Returning the inputs here seems like a bad abstraction
        return offer, dummy_psbt_decoded["inputs"], pubkey

    def _dummy_psbt(self, premium_amount, fund_amount, fund=False):
        # Create dummy PSBT to extract 'funding' UTXO and change addresses
        dummy_address = self._lnd_rpc.lnd.NewAddress(
            lnmsg.NewAddressRequest(type=lnmsg.AddressType.NESTED_PUBKEY_HASH)
        ).address
        amount = fund_amount if fund else premium_amount
        tx_template = walletmsg.TxTemplate(outputs={str(dummy_address): amount})
        psbt_request = walletmsg.FundPsbtRequest(raw=tx_template, target_conf=6)
        dummy_psbt = self._lnd_rpc.wallet.FundPsbt(request=psbt_request)
        dummy_psbt_b64 = base64.b64encode(dummy_psbt.funded_psbt).decode()
        dummy_psbt_decoded = self._brpc._proxy._call("decodepsbt", dummy_psbt_b64)
        return dummy_psbt, dummy_psbt_decoded


class OfferValidator:
    # TODO: Remove dependency on bitcoin rpc
    def __init__(self, lnd_rpc: LndRpc, btc_rpc: Proxy):
        self._lnd_rpc = lnd_rpc
        self._brpc = btc_rpc

    def validate(self, offer: Offer) -> bool:
        # XXX: For simplicity assume single input
        # check that utxo has not been spent
        utxo = self._brpc.gettxout(offer.inputs[0].prevout)
        if utxo is None:
            return False

        # TODO: For simplicity we just support one direction/role
        if offer.offer_type != OfferType.InboundLiquidity:
            return False

        return True

    # TODO: Remove internal asserts, either throw errors, or return False w/ errors
    def validate_offer_response(
        self, offer: Offer, offer_response: OfferResponse
    ) -> bool:
        assert offer.offer_id == offer_response.offer_id

        # check connection
        peers = self._lnd_rpc.lnd.ListPeers(lnmsg.ListPeersRequest())
        assert peers.peers[0].pub_key == offer_response.node_pubkey

        # TODO: we should also check `node_host`
        # ...

        tx = offer_response.funding_tx

        # XXX: this will not be true as we support batch transactions
        assert len(offer_response.signed_witness.vtxinwit) == 1

        # check that our input was included. For simplicity assume we are the last
        assert tx.vin[-1] == offer.inputs[0]

        # check that our change output was included
        assert tx.vout[-1] == offer.change_output

        # check that signature is valid. For simplicity just check that it's present
        assert tx.wit is not None

        premium_amount = offer.premium_amount
        fund_amount = offer.fund_amount

        taker_pubkey = offer.chan_pubkey
        maker_pubkey = offer_response.chan_pubkey

        # https://github.com/lightningnetwork/lightning-rfc/blob/master/03-transactions.md#funding-transaction-output
        # https://github.com/bitcoin/bips/blob/master/bip-0069.mediawiki
        if list(maker_pubkey) > list(taker_pubkey):
            pk1, pk2 = taker_pubkey, maker_pubkey
        else:
            pk1, pk2 = maker_pubkey, taker_pubkey

        msig_script = bs.CScript([bs.OP_2, pk1, pk2, bs.OP_2, bs.OP_CHECKMULTISIG])

        # convert to P2WSH
        script_pubkey = bc.CScript([bs.OP_0, hashlib.sha256(msig_script).digest()])
        assert script_pubkey.is_witness_v0_scripthash()

        funding_output = bc.CTxOut(premium_amount + fund_amount, script_pubkey)
        assert funding_output == tx.vout[0]
"""
