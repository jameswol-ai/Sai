from core.market import MarketEngine
from core.predictor import SaiBrain
from core.strategy import StrategyEngine
from core.risk import RiskEngine
from core.memory import SaiMemory

import time


print("SAI AI Trading Engine Starting...")


market = MarketEngine()
brain = SaiBrain()
strategy = StrategyEngine()
risk = RiskEngine()
memory = SaiMemory()


while True:

    try:

        data = market.get_market()


        prediction = brain.analyze(
            data
        )


        decision = strategy.decide(
            prediction
        )


        approved = risk.check(
            decision
        )


        result = {

            "market": data,

            "prediction": prediction,

            "decision": decision,

            "approved": approved

        }


        memory.save(
            result
        )


        print(result)


        time.sleep(10)


    except Exception as e:

        print(
            "SAI Error:",
            e
        )

        time.sleep(5)