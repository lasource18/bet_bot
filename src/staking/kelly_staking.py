from staking.staking import Staking

from decimal import getcontext, Decimal

getcontext().prec = 3

class KellyStaking(Staking):
    FRAC_KELLY = 0.1

    def __init__(self, bk, **kwargs) -> None:
        super().__init__(bk)
        self.value = kwargs.get('value', 0)
        self.odds = kwargs.get('odds', 0)
    
    def compute(self):
        if self.odds == 0:
            return 0.0
        return float(Decimal(self.bk) * Decimal(self.FRAC_KELLY) * (Decimal(self.value) / (Decimal(self.odds) - 1)))