import hashlib
import bitcoin.core.script as bs
import bitcoin.wallet as bw

from .lnd_rpc import walletmsg


def create_dummy_p2wpkh_address():
    # Create dummy P2WPKH address to call FundPsbt api
    h = hashlib.sha256(b"correct horse battery staple").digest()
    seckey = bw.CBitcoinSecret.from_secret_bytes(h)

    # Create an address from that private key.
    public_key = seckey.pub
    scriptPubKey = bs.CScript([bs.OP_0, bs.Hash160(public_key)])
    dummy_address = bw.P2WPKHBitcoinAddress.from_scriptPubKey(scriptPubKey)
    return dummy_address


def next_pubkey(lnd):
    """Derive the next pubkey within the key family account (rel: BIP43 and BIP32)."""
    # `key_family=0` is the `KeyFamilyMultiSig` (https://git.io/J3HJ5)
    key_req = walletmsg.KeyReq(key_family=0)
    key_desc = lnd.wallet.DeriveNextKey(key_req)
    return key_desc
