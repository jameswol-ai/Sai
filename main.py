from core.sai_core import SaiCore
from core.market import MarketEngine
import time


sai = SaiCore()

market = MarketEngine()


print("SAI Autonomous Agent System Online")


while True:


    data = market.get_market()


    result = sai.think(data)


    print(
        result
    )


    time.sleep(10)