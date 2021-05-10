import hashlib
import dataclasses
from dataclasses import dataclass

import bitcoin.core.script as bs
import bitcoin.wallet as bw
from bitcoin.rpc import hexlify, unhexlify

from .lnd_rpc import lnmsg, walletmsg


@dataclass(frozen=True)
class KeyDescriptor:
    raw_key_bytes: bytes
    key_family: int
    key_index: int

    @classmethod
    def from_json(cls, js):
        return cls(
            raw_key_bytes=unhexlify(js["raw_key_bytes"]),
            key_family=js["key_family"],
            key_index=js["key_index"],
        )

    @classmethod
    def from_pb(cls, pb):
        return cls(
            raw_key_bytes=pb.raw_key_bytes,
            key_family=pb.key_loc.key_family,
            key_index=pb.key_loc.key_index,
        )

    def to_json(self):
        desc = dataclasses.asdict(self)
        desc["raw_key_bytes"] = hexlify(desc["raw_key_bytes"])
        return desc

    def to_pb(self):
        return lnmsg.KeyDescriptor(
            raw_key_bytes=self.raw_key_bytes,
            key_loc=lnmsg.KeyLocator(
                key_family=self.key_family,
                key_index=self.key_index,
            ),
        )


def create_dummy_p2wpkh_address():
    # Create dummy P2WPKH address to call FundPsbt api
    h = hashlib.sha256(b"correct horse battery staple").digest()
    seckey = bw.CBitcoinSecret.from_secret_bytes(h)

    # Create an address from that private key.
    public_key = seckey.pub
    scriptPubKey = bs.CScript([bs.OP_0, bs.Hash160(public_key)])
    dummy_address = bw.P2WPKHBitcoinAddress.from_scriptPubKey(scriptPubKey)
    return dummy_address


def next_key_desc(lnd):
    """Derive the next pubkey within the key family account (rel: BIP43 and BIP32)."""
    # `key_family=0` is the `KeyFamilyMultiSig` (https://git.io/J3HJ5)
    key_req = walletmsg.KeyReq(key_family=0)
    key_desc = lnd.wallet.DeriveNextKey(key_req)
    key_desc = KeyDescriptor.from_pb(key_desc)
    return key_desc
