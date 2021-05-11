import json
import base64
from typing import Sequence
from dataclasses import dataclass

from bitcointx.core.psbt import PSBT_ProprietaryTypeData

from .lnd_rpc import signmsg
from .address import KeyDescriptor
from .signing import sign_message, verify_message


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
    channel_pubkey_key_desc: KeyDescriptor

    def serialize(self):
        offer = self.__dict__.copy()
        key_desc = offer["channel_pubkey_key_desc"]
        offer["channel_pubkey_key_desc"] = key_desc.to_json()
        offer = json.dumps(offer).encode()
        return base64.b64encode(offer)

    @classmethod
    def deserialize(cls, offer):
        offer = base64.b64decode(offer)
        offer = json.loads(offer)
        key_desc = offer["channel_pubkey_key_desc"]
        offer["channel_pubkey_key_desc"] = KeyDescriptor.from_json(key_desc)
        offer = cls(**offer)
        return offer

    def sign(self, key_desc, lnd):
        """Sign the offer with the given key returning a signed digest (signature)."""
        key_locator = key_desc.to_pb().key_loc
        key_locator = signmsg.KeyLocator(
            key_family=key_locator.key_family, key_index=key_locator.key_index
        )
        signature = sign_message(self.serialize(), key_locator, lnd)
        return signature

    def verify(self, signature, pubkey, lnd):
        valid = verify_message(self.serialize(), signature, pubkey, lnd)
        return valid


@dataclass(frozen=True)
class OfferReply(Offer):
    channel_id: str


def attach_offer_to_psbt(offer, psbt, lnd):
    """Serializes the offer and attaches it to the proprietary fields of the PSBT in
    place.
    """
    offer_serialize = offer.serialize()
    signature = offer.sign(offer.channel_pubkey_key_desc, lnd)
    psbt.proprietary_fields[b"offer"] = [
        PSBT_ProprietaryTypeData(0, b"params", offer_serialize),
        PSBT_ProprietaryTypeData(0, b"signature", signature),
    ]


def attach_offer_reply_to_psbt(offer_reply, psbt, lnd):
    """Serializes the offer reply and attaches it to the PSBT in place."""
    reply_serialize = offer_reply.serialize()
    signature = offer_reply.sign(offer_reply.channel_pubkey_key_desc, lnd)
    psbt.proprietary_fields[b"reply"] = [
        PSBT_ProprietaryTypeData(0, b"params", reply_serialize),
        PSBT_ProprietaryTypeData(0, b"signature", signature),
    ]


def get_offer_from_psbt(psbt):
    offer = psbt.proprietary_fields[b"offer"][0].value
    offer = Offer.deserialize(offer)
    return offer


def get_offer_reply_from_psbt(psbt):
    reply = psbt.proprietary_fields[b"reply"][0].value
    reply = OfferReply.deserialize(reply)
    return reply


def validate_offer_psbt(offer_psbt):
    # check that funding UTXOs has not been spent
    # note we can't use `lnd.GetTransactions` since it only knows about our wallet's transactions
    # it's probably safe to skip this step because blockchain will prevent from double spending
    #
    # for vin in psbt1.unsigned_tx.vin:
    #     utxo = brpc.gettxout(vin.prevout)
    #     assert utxo is not None
    #
    offer = get_offer_from_psbt(offer_psbt)
    fees_amount = offer_psbt.get_fee() - offer.premium_amount
    if fees_amount <= 0:
        raise RuntimeError(
            f"Offer PSBT does not incorporate sufficient fees (fees={fees_amount})"
        )


def validate_offer_was_not_tampered(psbt, lnd):
    offer, signature = psbt.proprietary_fields[b"offer"]
    offer, signature = Offer.deserialize(offer.value), signature.value

    valid = offer.verify(signature, offer.channel_pubkey_key_desc.raw_key_bytes, lnd)
    if not valid:
        raise RuntimeError(
            "The received offer has an invalid signature. It may have been "
            + "tampered with."
        )


def validate_offer_reply_was_not_tampered(psbt, lnd):
    reply, signature = psbt.proprietary_fields[b"reply"]
    reply, signature = OfferReply.deserialize(reply.value), signature.value

    valid = reply.verify(signature, reply.channel_pubkey_key_desc.raw_key_bytes, lnd)
    if not valid:
        raise RuntimeError(
            "The received offer reply has an invalid signature. It may have been "
            + "tampered with."
        )
