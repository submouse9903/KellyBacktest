"""Utility models and helpers for the Lean algorithm."""

import json
from AlgorithmImports import *


class CustomFeeModel(FeeModel):
    def __init__(self, commission_rate=0.0015):
        self.commission_rate = commission_rate

    def GetOrderFee(self, parameters):
        order = parameters.Order
        security = parameters.Security
        fee = abs(order.AbsoluteQuantity * order.Price) * self.commission_rate
        return OrderFee(CashAmount(fee, security.Symbol.Value))


class CustomSlippageModel:
    def __init__(self, slippage_rate=0.0005):
        self.slippage_rate = slippage_rate

    def GetSlippageApproximation(self, asset, order):
        return asset.Price * self.slippage_rate


def save_results(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
