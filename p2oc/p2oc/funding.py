import hashlib

import bitcointx.core as bc
import bitcointx.core.script as bs

def create_funding_output(
    taker_pubkey,
    maker_pubkey,
    premium_amount,
    fund_amount,
):
    # References: https://git.io/J3HsI (LND) https://git.io/J3Hs4 (BIP69)
    if list(maker_pubkey) > list(taker_pubkey):
        pk1, pk2 = taker_pubkey, maker_pubkey
    else:
        pk1, pk2 = maker_pubkey, taker_pubkey

    msig_script = bs.CScript([bs.OP_2, pk1, pk2, bs.OP_2, bs.OP_CHECKMULTISIG])

    # Convert to P2WSH
    script_pubkey = bs.CScript([bs.OP_0, hashlib.sha256(msig_script).digest()])

    if not script_pubkey.is_witness_v0_scripthash():
        raise RuntimeError("Funding transaction is not using P2WSH.")

    funding_output = bc.CTxOut(premium_amount + fund_amount, script_pubkey)
    return funding_output
