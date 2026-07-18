class StrategyAgent:


    def decide(self, market):


        if market["activity"]=="HIGH":

            return {

                "signal":"BUY",

                "reason":
                "High market activity"

            }


        return {

            "signal":"WAIT",

            "reason":
            "Low activity"

        }