# plugins/prediction/fx_lstm.py
import numpy as np
import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

def train_lstm(series, epochs=5, lookback=30):
    # Minimal training loop placeholder
    model = LSTMModel()
    return model

def forecast(model, series, steps=7, lookback=30):
    # Dummy forecast: repeat last value
    last_val = series[-1]
    return [last_val for _ in range(steps)]
