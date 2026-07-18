import joblib
import os
from config.settings import MODEL_PATH


class TradingAI:

    def __init__(self):
        self.model = None
        self.load()

    def load(self):

        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
        else:
            self.model = None


    def predict(self, data):

        if self.model is None:
            return {
                "signal":"WAIT",
                "confidence":0
            }

        result = self.model.predict(data)

        return {
            "signal":str(result[0]),
            "confidence":0.85
        }