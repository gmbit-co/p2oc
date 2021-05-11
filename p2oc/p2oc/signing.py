import bitcointx.core.script as bs
import bitcointx.core as bc
import bitcoin.wallet as bw
from bitcointx.core.psbt import PartiallySignedTransaction

from .lnd_rpc import signmsg, walletmsg
from .address import create_dummy_p2wpkh_address


def allocate_funds(amount, lnd, include_tx_fee=True, min_confirmations=6):
    """Create a PSBT via the provided LND's wallet. The PSBT will be unsigned and have
    a single output to the change address. The PSBT fee (difference between input and
    output amount) will be of the given amount + the tx fee to publish this PSBT.
    Including tx fee is configurable so as to have this or the other party pay fees.
    """
    # TODO: In the future refactor to explicitly create a placeholder output w/ a null
    #       output but correct value. We will change the output address later.

    # Use a dummy address to extract "funding" UTXO and change addresses
    dummy_address = create_dummy_p2wpkh_address()
    tx_template = walletmsg.TxTemplate(outputs={str(dummy_address): amount})

    if include_tx_fee:
        psbt_request = walletmsg.FundPsbtRequest(
            raw=tx_template, target_conf=6, min_confs=min_confirmations
        )
    else:
        # XXX: Setting the `sat_per_vbyte` to 0 fails because 0 is a null value in
        #      Golang for the int type. As a result we need to set it to some
        #      non-zero value.
        psbt_request = walletmsg.FundPsbtRequest(
            raw=tx_template, sat_per_vbyte=1, min_confs=min_confirmations
        )

    psbt = lnd.wallet.FundPsbt(request=psbt_request)

    change_output_index = psbt.change_output_index

    # Convert from LND PSBT to Python bitcointx PSBT data structure
    psbt = PartiallySignedTransaction.from_binary(psbt.funded_psbt)

    # Remove dummy output
    if len(psbt.unsigned_tx.vout) != 2:
        raise RuntimeError(
            "Change-only PSBT during construction must have 2 vouts (vout="
            + f"{len(psbt.unsigned_tx.vout)}) (change and dummy to allocate enough fee "
            + "for the given amount)."
        )

    # Add change output
    tx = bc.CMutableTransaction.from_instance(psbt.unsigned_tx)
    tx.vout = [psbt.unsigned_tx.vout[change_output_index]]

    original_fee = psbt.get_fee()

    # Update PSBT
    psbt.unsigned_tx = tx
    psbt.outputs = [psbt.outputs[change_output_index]]
    psbt.outputs[0].index = 0

    # Ensure that the dummy output for premium was removed
    if psbt.get_fee() != original_fee + amount:
        raise RuntimeError(
            f"Change-only PSBT does not have a fee ({psbt.get_fee()}) that matches "
            + f"the given fee amount={amount} + the transaction fee={original_fee}."
        )

    return psbt


def sign_message(message, key_loc, lnd):
    resp = lnd.signer.SignMessage(signmsg.SignMessageReq(msg=message, key_loc=key_loc))
    return resp.signature


def verify_message(message, signature, pubkey, lnd):
    resp = lnd.signer.VerifyMessage(
        signmsg.VerifyMessageReq(msg=message, signature=signature, pubkey=pubkey)
    )
    return resp.valid


def sign_inputs(psbt, input_indices, key_desc, lnd):
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


def copy_inputs(from_psbt, to_psbt):
    """Copy inputs from `from_psbt` into `to_psbt` (and do so in place)."""
    for i, vin in enumerate(from_psbt.unsigned_tx.vin):
        inp = from_psbt.inputs[i]
        # XXX: Reset index (an implementation detail of bitcointx to have it it
        #      re-calculate the index position).
        inp.index = None
        to_psbt.add_input(vin, inp)

    for i, vout in enumerate(from_psbt.unsigned_tx.vout):
        out = from_psbt.outputs[i]
        out.index = None
        to_psbt.add_output(vout, out)


def finalize_and_publish_psbt(psbt, lnd):
    tx = bc.CMutableTransaction.from_instance(psbt.unsigned_tx)

    wits = [inp.final_script_witness for inp in psbt.inputs]
    wits = [bc.CTxInWitness(wit) for wit in wits]
    tx.wit = bc.CTxWitness(wits)

    lnd.wallet.PublishTransaction(walletmsg.Transaction(tx_hex=tx.serialize()))
