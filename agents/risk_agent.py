class RiskAgent:


    def evaluate(
        self,
        trade
    ):


        if trade["signal"]=="BUY":


            return {

                "approved":True,

                "risk":"LOW"

            }


        return {

            "approved":False,

            "risk":"HIGH"

            }