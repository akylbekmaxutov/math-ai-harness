"""Budget, enforced at the tool boundary.

Instructions do not constrain spend; boundaries do. Telling a model "keep it
under fifty cents" is a request. Refusing the next tool call is a limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    def __init__(self, spent: float, cap: float, kind: str):
        super().__init__(f"{kind} budget exceeded: {spent:.4f} of {cap:.4f}")
        self.spent, self.cap, self.kind = spent, cap, kind


@dataclass
class Budget:
    usd_cap: float
    turn_cap: int
    usd_spent: float = 0.0
    turns_used: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    trips: list[str] = field(default_factory=list)

    def charge(self, tokens_in: int, tokens_out: int, usd: float) -> None:
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.usd_spent += usd

    def check(self, kind: str = "usd") -> None:
        """Called immediately before a tool executes and before each turn."""
        if self.usd_spent >= self.usd_cap:
            self.trips.append("usd")
            raise BudgetExceeded(self.usd_spent, self.usd_cap, "usd")
        if self.turns_used >= self.turn_cap:
            self.trips.append("turns")
            raise BudgetExceeded(self.turns_used, self.turn_cap, "turn")

    def snapshot(self) -> dict:
        return {
            "usd": round(self.usd_spent, 6),
            "turns": self.turns_used,
            "tool_calls": self.tool_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
        }
