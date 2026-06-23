# plugins/prediction/fx_lstm.py
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])  # last time step
        return out

def prepare_data(series, lookback=30):
    X, y = [], []
    for i in range(len(series) - lookback):
        X.append(series[i:i+lookback])
        y.append(series[i+lookback])
    X = np.array(X).reshape(-1, lookback, 1)
    y = np.array(y).reshape(-1, 1)
    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

def train_lstm(series, epochs=20, lookback=30):
    X, y = prepare_data(series, lookback)
    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(epochs):
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            output = model(batch_X)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()

    return model

def forecast(model, series, lookback=30, steps=7):
    inputs = torch.tensor(series[-lookback:], dtype=torch.float32).reshape(1, lookback, 1)
    preds = []
    for _ in range(steps):
        out = model(inputs)
        preds.append(out.item())
        inputs = torch.cat([inputs[:,1:,:], out.reshape(1,1,1)], dim=1)
    return preds
