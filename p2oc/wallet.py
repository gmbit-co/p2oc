import bitcointx.core as bc
from bitcointx.core.psbt import PartiallySignedTransaction

from .lnd_rpc import signmsg, walletmsg
from .address import create_dummy_p2wpkh_address


def allocate_funds(amount, lnd, include_tx_fee=True, min_confirmations=6):
    """Create a PSBT via the provided LND's wallet. The PSBT will be unsigned
    and have a single output to the change address. This PSBT secures enough
    funds at its inputs such that later when an additional output with the given
    `amount` is attached and the final tx will have sufficient fees.

    Setting `include_tx_fee=True` will include regular tx fee calculated by
    the wallet based on the current on-chain fees, the size of all inputs and 2
    outputs (dummy + change)

    `min_confirmations` is passed to the wallet and used for fee calculation.
    """
    # TODO: In the future refactor to explicitly create a placeholder output w/ a null
    #       output but correct value. We will change the output address later.

    # Use a dummy address to extract "funding" UTXO and change addresses
    dummy_address = create_dummy_p2wpkh_address()
    tx_template = walletmsg.TxTemplate(outputs={str(dummy_address): amount})

    psbt_request = walletmsg.FundPsbtRequest(
        raw=tx_template, target_conf=6, min_confs=min_confirmations
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
    change_output = psbt.unsigned_tx.vout[change_output_index]
    change_output = bc.CMutableTxOut.from_instance(change_output)
    tx.vout = [change_output]

    original_fee = psbt.get_fee()

    if not include_tx_fee:
        # remove tx fee by adding the fee amount to the change output
        tx.vout[0].nValue += psbt.get_fee()
        original_fee = 0

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


def estimate_fee(lnd, conf_target=6):
    fee_req = walletmsg.EstimateFeeRequest(conf_target=conf_target)
    resp = lnd.wallet.EstimateFee(fee_req)
    sat_per_vbyte = resp.sat_per_kw * 4 / 1000  # 1 vbyte = 4 weight units
    return int(sat_per_vbyte)
