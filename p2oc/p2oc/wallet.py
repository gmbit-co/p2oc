import bitcointx.core as bc
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
