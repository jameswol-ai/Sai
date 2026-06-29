# =========================================================
# SAI V3 — EVOLUTIONARY INTELLIGENCE CORE
# Genetic Multi-Agent Trading System
# =========================================================

import random
import copy
import math

# =========================================================
# FEATURES ENGINE
# =========================================================

def compute_features(data):
    returns = [data[i] - data[i-1] for i in range(1, len(data))]

    momentum = sum(returns[-5:]) if len(returns) >= 5 else sum(returns)
    volatility = sum(abs(r) for r in returns[-5:]) / 5 if len(returns) >= 5 else 1
    trend = (data[-1] - data[0]) / len(data)

    return {
        "momentum": momentum,
        "volatility": volatility,
        "trend": trend
    }

# =========================================================
# AGENT SPECIES
# =========================================================

class Agent:
    def __init__(self, name):
        self.name = name
        self.weight = random.uniform(0.5, 1.5)
        self.fitness = 1.0

    def vote(self, f):
        return 0

    def mutate(self):
        child = copy.deepcopy(self)
        child.weight += random.uniform(-0.2, 0.2)
        child.weight = max(0.1, child.weight)
        child.fitness = 1.0
        child.name = self.name + "_m"
        return child

# ---------------------------------------------------------
# SPECIALIZED AGENTS
# ---------------------------------------------------------

class MomentumAgent(Agent):
    def vote(self, f):
        return self.weight * (1 if f["momentum"] > 0 else -1)

class MeanReversionAgent(Agent):
    def vote(self, f):
        return self.weight * (-1 if f["momentum"] > 0 else 1)

class RiskAgent(Agent):
    def vote(self, f):
        return self.weight * (-1 if f["volatility"] > 2 else 0.5)

class TrendAgent(Agent):
    def vote(self, f):
        return self.weight * (1 if f["trend"] > 0 else -1)

class NoiseAgent(Agent):
    def vote(self, f):
        return self.weight * random.uniform(-1, 1)

# =========================================================
# EVOLUTION CORE
# =========================================================

class EvolutionEngine:
    def __init__(self):
        self.population = [
            MomentumAgent("momentum"),
            MeanReversionAgent("reversion"),
            RiskAgent("risk"),
            TrendAgent("trend"),
            NoiseAgent("noise")
        ]

    def evaluate(self, data):
        features = compute_features(data)
        votes = []
        decision_score = 0

        for agent in self.population:
            v = agent.vote(features)
            votes.append((agent, v))
            decision_score += v

        decision = "HOLD"
        if decision_score > 1:
            decision = "BUY"
        elif decision_score < -1:
            decision = "SELL"

        return decision, votes, features

    def assign_fitness(self, market_return):
        # reward correct directional bias
        for agent in self.population:
            agent.fitness *= (1 + market_return * random.uniform(0.8, 1.2))

    def cull(self):
        self.population.sort(key=lambda a: a.fitness, reverse=True)
        self.population = self.population[:4]  # survival pressure

    def reproduce(self):
        if len(self.population) < 6:
            parent = random.choice(self.population)
            self.population.append(parent.mutate())

    def evolve(self, market_return):
        self.assign_fitness(market_return)
        self.cull()
        self.reproduce()

# =========================================================
# MAIN SAI V3 ENGINE
# =========================================================

engine = EvolutionEngine()

def sai_v3_step(data):
    decision, votes, features = engine.evaluate(data)

    # fake market reward signal (replace with real PnL later)
    market_return = random.uniform(-0.05, 0.05)

    engine.evolve(market_return)

    return {
        "decision": decision,
        "votes": {a.name: round(v, 3) for a, v in votes},
        "features": features,
        "population_size": len(engine.population)
    }