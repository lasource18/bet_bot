from staking.staking import Staking

from decimal import getcontext, Decimal

class KellyStaking(Staking):
    FRAC_KELLY = 0.1

    def __init__(self, bk, **kwargs) -> None:
        super(Staking, self).__init__(bk)
        self.value = kwargs.get('value', 0)
        self.odds = kwargs.get('odds', 0)
    
    def compute(self):
        if self.odds == 0:
            return 0.0
        getcontext().prec = 2
        return float(Decimal(self.bk) * Decimal(self.FRAC_KELLY) * (Decimal(self.value) / (Decimal(self.odds) - 1)))