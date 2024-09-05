from staking.staking import Staking

class LevelStaking(Staking):
    AMOUNT = 10

    def __init__(self, bk, **kwargs) -> None:
        super().__init__(bk)
    
    def compute(self):
        return self.AMOUNT