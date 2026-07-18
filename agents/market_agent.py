class MarketAgent:


    def analyze(self, market):

        price = market["price"]
        volume = market["volume"]


        if volume > 3000:

            activity = "HIGH"

        else:

            activity = "NORMAL"


        return {

            "price":price,

            "activity":activity

        }