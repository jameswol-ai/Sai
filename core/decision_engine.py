class DecisionEngine:


    def decide(
        self,
        strategy,
        risk
    ):


        if (
            strategy["signal"]=="BUY"
            and
            risk["approved"]
        ):


            return {

                "action":"EXECUTE",

                "signal":"BUY"

            }



        return {

            "action":"HOLD",

            "signal":"WAIT"

        }