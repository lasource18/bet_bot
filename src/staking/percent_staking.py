from staking.staking import Staking

from decimal import getcontext, Decimal

class PercentStaking(Staking):
    PERCENT = 0.1

    def __init__(self, bk, **kwargs) -> None:
        super().__init__(bk)
    
    def compute(self):
        getcontext().prec = 3
        return float(Decimal(self.PERCENT) * Decimal(self.bk))