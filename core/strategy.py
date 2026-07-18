class StrategyEngine:


    def decide(self,prediction):


        if prediction["signal"]=="BUY":


            return {

                "action":"OPEN_LONG",

                "size":1

            }


        elif prediction["signal"]=="SELL":


            return {

                "action":"OPEN_SHORT",

                "size":1

            }


        return {

            "action":"HOLD",

            "size":0

        }