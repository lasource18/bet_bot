from staking.kelly_staking import KellyStaking

class StakingFactory(object):
    def select_staking_strategy(self, bk: float, method: str, **kwargs):
        staking_strategy = get_staking_strategy(method)
        return staking_strategy(bk, kwargs)

def get_staking_strategy(method: str):
    if method.lower() == 'kelly':
        return KellyStaking
    else:
        raise ValueError(method)