import math
from typing import Dict, NamedTuple
import uuid
from enum import Enum
from limit_order_book import LimitOrderBook as LimitOrderBook_
from limit_order_book.library import Library

class LimitOrderBook(LimitOrderBook_):
    # Doesn't work, causes a crash
    def get(self, order_id):
        pointer = Library.functions.get(self._book, order_id)
        return pointer


class OrderSide(Enum):
    BID = True
    ASK = False


class OrderAccount(NamedTuple):
    """public key of account doing bidding or asking."""

    pubkey: str
    """lightning node network endpoint of seller or buyer (of of the buyer's
    choosing, e.g. for sidecar channels)."""
    node_endpoint: str


class Order(NamedTuple):
    side: OrderSide
    quantity: int
    per_unit_fees: int  # In satoshis
    by: OrderAccount


class Accounts:
    def __init__(self) -> None:
        self._order_id_to_account: Dict[str, str] = {}

    def add_account(self, order_id, account: OrderAccount):
        self._order_id_to_account[order_id] = account

    def account(self, order_id):
        return self._order_id_to_account.get(order_id)


class OrderEngine:
    SATOSHIS_PER_UNIT = 1000

    def __init__(self) -> None:
        self.book = LimitOrderBook()
        self.accounts = Accounts()

    @staticmethod
    def _gen_id():
        # Taken from https://stackoverflow.com/a/3530326/2783780 (right-shifting by
        # 64 bits removes the MAC address and time, leaving only the clock. 64-bit
        # is also a requirement from the limit order book library.
        return uuid.uuid1().int >> 64

    def limit(self, order: Order) -> str:
        """
        quantity: number of units of liquidity, each unit being 1k (SATOSHIS_PER_UNIT)
                  satoshis in size
        per_unit_fee: the price paid (upfront) to lease one unit of liquidity
        """
        order_id = OrderEngine._gen_id()
        self.book.limit(order.side.value, order_id, order.quantity, order.per_unit_fees)
        self.accounts.add_account(order_id, order.by)
        return order_id


class Conversions:
    SATOSHIS_PER_BTC = 100000000

    @staticmethod
    def btc_to_order_quantity(btc) -> int:
        units = (
            math.floor(btc * Conversions.SATOSHIS_PER_BTC)
            / OrderEngine.SATOSHIS_PER_UNIT
        )
        return math.floor(units)
