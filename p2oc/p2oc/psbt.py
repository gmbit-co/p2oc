import bitcointx.core as bc

from .lnd_rpc import walletmsg


from bitcointx.core.psbt import PartiallySignedTransaction


def deserialize_psbt(psbt):
    return PartiallySignedTransaction.from_base64(psbt)


def merge_psbts(from_psbt, to_psbt):
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
