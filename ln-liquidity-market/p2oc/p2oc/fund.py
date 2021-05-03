import hashlib

import bitcoin.core as bc
import bitcoin.core.script as bs
import bitcoin.wallet as bw
from bitcoin.rpc import unhexlify

from .lnd_rpc import signmsg


class FundingTx:
    def __init__(self, lnd_rpc, btc_rpc):
        self._lnd_rpc = lnd_rpc
        self._btc_rpc = btc_rpc

    def create(
        self,
        maker_pubkey,
        taker_pubkey,
        premium_amount,
        fund_amount,
        maker_inputs,
        taker_inputs,
        maker_change_output,
        taker_change_output,
    ):
        # https://github.com/lightningnetwork/lightning-rfc/blob/master/03-transactions.md#funding-transaction-output
        # https://github.com/bitcoin/bips/blob/master/bip-0069.mediawiki
        # if makerPubKey > takerPubKey:
        if list(maker_pubkey) > list(taker_pubkey):
            pk1, pk2 = taker_pubkey, maker_pubkey
        else:
            pk1, pk2 = maker_pubkey, taker_pubkey

        msig_script = bs.CScript([bs.OP_2, pk1, pk2, bs.OP_2, bs.OP_CHECKMULTISIG])

        # convert to P2WSH
        script_pubkey = bc.CScript([bs.OP_0, hashlib.sha256(msig_script).digest()])

        assert script_pubkey.is_witness_v0_scripthash()

        funding_output = bc.CTxOut(premium_amount + fund_amount, script_pubkey)

        funding_tx_inputs = maker_inputs + taker_inputs
        funding_tx_outputs = [funding_output, maker_change_output, taker_change_output]
        # TODO: For simplicity maker's input is at position 0
        funding_output_idx = 0

        funding_tx = bc.CTransaction(funding_tx_inputs, funding_tx_outputs)
        return funding_tx, funding_output_idx

    def signed_witness(self, funding_inputs, funding_tx, input_idx):
        # assume single input for simplicity
        assert len(funding_inputs) == 1
        input_ = funding_inputs[0]

        # our UTXO pubkey
        assert len(input_["bip32_derivs"]) == 1
        pubkey = input_["bip32_derivs"][0]["pubkey"]
        pubkey = unhexlify(pubkey)

        utxo_addr = input_["witness_utxo"]["scriptPubKey"]["address"]
        utxo_addr = bw.CBitcoinAddress(utxo_addr)

        sign_desc = signmsg.SignDescriptor(
            key_desc=signmsg.KeyDescriptor(raw_key_bytes=pubkey),
            witness_script=utxo_addr.to_redeemScript(),
            output=signmsg.TxOut(
                value=int(input_["witness_utxo"]["amount"] * bc.COIN),
                pk_script=utxo_addr.to_scriptPubKey(),
            ),
            sighash=bs.SIGHASH_ALL,  # so that transaction cannot be altered
            input_index=input_idx,
        )

        signReq = signmsg.SignReq(
            raw_tx_bytes=funding_tx.serialize(), sign_descs=[sign_desc]
        )

        sign_resp = self._lnd_rpc.signer.SignOutputRaw(signReq)
        signature = sign_resp.raw_sigs[0] + bytes([bs.SIGHASH_ALL])
        witness = [signature, pubkey]
        witness = bc.CTxWitness([bc.CTxInWitness(bs.CScriptWitness(witness))])
        return witness

    def create_signed_funding_tx(self, funding_tx, signed_witnesses):
        final_funding_tx = bc.CMutableTransaction.from_tx(funding_tx)
        final_funding_tx.wit = bc.CTxWitness(signed_witnesses)
        return final_funding_tx

    def publish(self, signed_funding_tx):
        final_funding_tx_id = self._btc_rpc.sendrawtransaction(signed_funding_tx)
        return final_funding_tx_id
