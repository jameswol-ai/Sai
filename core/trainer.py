import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier


class Trainer:


    def train(self,file):


        df=pd.read_csv(file)


        X=df[
            [
            "price",
            "volume",
            "MA20"
            ]
        ]


        y=df["signal"]



        model=RandomForestClassifier(
            n_estimators=100
        )


        model.fit(
            X,
            y
        )


        joblib.dump(
            model,
            "models/model.pkl"
        )


        return "Training Complete"