import random


class SaiBrain:


    def analyze(self, market):


        confidence = random.randint(
            60,
            95
        )


        if confidence > 80:

            signal="BUY"

        elif confidence < 70:

            signal="SELL"

        else:

            signal="WAIT"



        return {

            "signal":signal,

            "confidence":confidence,

            "price":
                market["price"]

        }