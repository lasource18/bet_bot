from abc import abstractmethod

class Staking(object):
    def __init__(self, bk, **kwargs) -> None:
        self.bk = bk
    
    @abstractmethod
    def compute(self):
        raise NotImplementedError('Method is required!')