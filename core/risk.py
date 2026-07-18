class RiskEngine:


    def __init__(self):

        self.max_risk = 2



    def check(self,trade):


        if trade["size"] <= 1:

            return True


        return False