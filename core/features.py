import pandas as pd


class FeatureEngine:


    def create(self, history):


        df=pd.DataFrame(
            history
        )


        df["MA20"]=(
            df["price"]
            .rolling(20)
            .mean()
        )


        df["change"]=(
            df["price"]
            .pct_change()
        )


        return df.fillna(0)