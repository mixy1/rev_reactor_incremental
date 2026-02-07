from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResourceStore:
    money: float = 0.0
    total_money: float = 0.0
    money_earned_this_game: float = 0.0

    power: float = 0.0
    total_power_produced: float = 0.0
    power_produced_this_game: float = 0.0

    heat: float = 0.0
    total_heat_dissipated: float = 0.0
    heat_dissipated_this_game: float = 0.0

    exotic_particles: float = 0.0
    total_exotic_particles: float = 0.0

    last_power_change: float = 0.0
    last_heat_change: float = 0.0

    def add_money(self, amount: float) -> None:
        if amount <= 0.0:
            return
        self.money += amount
        self.total_money += amount
        self.money_earned_this_game += amount

    def add_power(self, amount: float) -> None:
        if amount == 0.0:
            return
        self.power += amount
        self.last_power_change = amount
        if amount > 0.0:
            self.total_power_produced += amount
            self.power_produced_this_game += amount

    def add_heat(self, amount: float) -> None:
        if amount == 0.0:
            return
        prev = self.heat
        self.heat = max(0.0, self.heat + amount)
        self.last_heat_change = amount
        if self.heat < prev:
            dissipated = prev - self.heat
            self.total_heat_dissipated += dissipated
            self.heat_dissipated_this_game += dissipated

    def drain_power(self, amount: float) -> float:
        if amount <= 0.0:
            return 0.0
        drained = min(self.power, amount)
        self.power -= drained
        return drained

    def dissipate_heat(self, amount: float) -> float:
        if amount <= 0.0:
            return 0.0
        prev = self.heat
        self.heat = max(0.0, self.heat - amount)
        dissipated = prev - self.heat
        if dissipated > 0.0:
            self.total_heat_dissipated += dissipated
            self.heat_dissipated_this_game += dissipated
            self.last_heat_change = -dissipated
        return dissipated
