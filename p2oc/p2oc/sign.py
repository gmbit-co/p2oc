import bitcoin.wallet as bw
import bitcointx.core.script as bs

from .lnd_rpc import signmsg


def sign_message(message, key_loc, lnd):
    resp = lnd.signer.SignMessage(signmsg.SignMessageReq(msg=message, key_loc=key_loc))
    return resp.signature


def verify_message(message, signature, pubkey, lnd):
    resp = lnd.signer.VerifyMessage(
        signmsg.VerifyMessageReq(msg=message, signature=signature, pubkey=pubkey)
    )
    return resp.valid


def sign_inputs(psbt, input_indices, lnd):
    """Signs all inputs of the given PSBT according to the supplied indices. This
    function mutates the PSBT in place (doesn't return a copy).
    """
    for idx in input_indices:
        inp = psbt.inputs[idx]

        if len(inp.derivation_map.keys()) != 1:
            raise RuntimeError(
                "A _single_ (== 1) deriviation path was not detected for the "
                + f"supplied input. This scenario is not presently handled.\n\n"
                + f"input={inp}\nderivation_map={inp.derivation_map}\n"
                + f"len(derivation_map)={len(inp.derivation_map)} != 1"
            )
        pubkey = list(inp.derivation_map.keys())[0]
        key_desc = signmsg.KeyDescriptor(raw_key_bytes=pubkey)

        utxo_addr = bw.CBitcoinAddress.from_scriptPubKey(inp.witness_utxo.scriptPubKey)

        sign_desc = signmsg.SignDescriptor(
            key_desc=key_desc,
            witness_script=utxo_addr.to_redeemScript(),
            output=signmsg.TxOut(
                value=inp.witness_utxo.nValue, pk_script=utxo_addr.to_scriptPubKey()
            ),
            sighash=bs.SIGHASH_ALL,  # so that transaction cannot be altered
            input_index=idx,
        )

        sign_req = signmsg.SignReq(
            raw_tx_bytes=psbt.unsigned_tx.serialize(), sign_descs=[sign_desc]
        )
        sign_resp = lnd.signer.SignOutputRaw(sign_req)

        signature = sign_resp.raw_sigs[0] + bytes([bs.SIGHASH_ALL])
        witness = [signature, pubkey]

        inp.final_script_witness = bs.CScriptWitness(witness)
        # XXX: We must remove 'bip32_derivs' since the bitcointx package does not like
        # that `final_script_witness` and `derivation_map` exist together.
        inp.derivation_map = {}
