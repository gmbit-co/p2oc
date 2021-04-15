import random
import bitcoin.core as bc
import bitcoin.core.script as bs

class User:
    def __init__(self, rpc):
        self.rpc = rpc
        self._secrets = []
        self.addresses = []
        self._password = str(hash(self) + random.uniform(0,1)).encode()

    def generate_addresses(self, n):
        for _ in range(n):
            addr = self.rpc.getnewaddress()
            secr = self.rpc.dumpprivkey(addr)
            self.addresses.append(addr)
            self._secrets.append(secr)

    def pub_key(self, key_id):
        return self._secrets[key_id].pub

    @property
    def utxos(self):
        txs = self.rpc.listunspent(addrs=self.addresses)
        return txs

    def utxo(self, amount):
        # find the right utxo given `amount`
        utxos = self.utxos
        amounts = [u['amount'] for u in utxos]
        utxo_id = amounts.index(amount)
        utxo = utxos[utxo_id]
        return utxo

    def sign_hash(self, key_id, sig_hash, sig_hash_type=bs.SIGHASH_ALL):
        assert key_id >= 0 and key_id < len(self._secrets)
        assert isinstance(sig_hash, bytes)

        secret = self._secrets[key_id]
        sig = secret.sign(sig_hash) + bytes([sig_hash_type])
        return sig

    def sign_utxo(self, utxo, tx, vin_id):
        # copy `tx`
        tx = bc.CMutableTransaction.from_tx(tx)
        # get required input
        txin = tx.vin[vin_id]
        assert txin.prevout == utxo['outpoint']

        addr = utxo['address']
        key_id = self.addresses.index(addr)
        secret = self._secrets[key_id]

        sighash = bs.SignatureHash(addr.to_scriptPubKey(),
                                   tx,
                                   vin_id,
                                   bs.SIGHASH_ALL)

        sig = secret.sign(sighash) + bytes([bs.SIGHASH_ALL])
        txin.scriptSig = bs.CScript([sig, secret.pub])
        return tx

    def hashed_password(self):
        return bc.Hash160(self._password)

    def reveal_password(self):
        return self._password
