"""LLM cost monitoring: per-customer spend tracking with budget enforcement.

Tracks token consumption and estimated cost per customer. When a customer
exceeds their daily budget, the system degrades gracefully by falling back
to MetaMap-only expansion (no LLM call) and flags the response.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Approximate cost per token (in cents) -- configurable per model
_DEFAULT_COST_PER_INPUT_TOKEN_CENTS = 0.0003  # $3/M input tokens
_DEFAULT_COST_PER_OUTPUT_TOKEN_CENTS = 0.0015  # $15/M output tokens

_DEFAULT_DAILY_BUDGET_CENTS = 1000.0  # $10/day


class CostRecord(BaseModel):
    """A single LLM usage record."""

    model_config = ConfigDict(frozen=True)

    customer_id: str
    timestamp: float
    input_tokens: int
    output_tokens: int
    estimated_cost_cents: float
    model: str
    operation: str


class CustomerBudgetStatus(BaseModel):
    """Budget status for a single customer."""

    model_config = ConfigDict(frozen=True)

    customer_id: str
    daily_budget_cents: float
    spent_today_cents: float
    remaining_cents: float
    over_budget: bool
    request_count_today: int


class CostDashboard(BaseModel):
    """Aggregated cost dashboard across all customers."""

    model_config = ConfigDict(frozen=True)

    total_spend_cents: float
    total_tokens: int
    customer_breakdown: dict[str, float]
    model_breakdown: dict[str, float]
    over_budget_customers: list[str]


class LlmCostMonitor:
    """Per-customer LLM cost tracking with budget enforcement."""

    def __init__(
        self,
        *,
        cost_per_input_token: float = _DEFAULT_COST_PER_INPUT_TOKEN_CENTS,
        cost_per_output_token: float = _DEFAULT_COST_PER_OUTPUT_TOKEN_CENTS,
    ) -> None:
        self._cost_per_input = cost_per_input_token
        self._cost_per_output = cost_per_output_token
        self._records: list[CostRecord] = []
        self._daily_budgets: dict[str, float] = {}

    def set_budget(self, customer_id: str, daily_budget_cents: float) -> None:
        """Set or update a customer's daily LLM budget."""
        self._daily_budgets[customer_id] = daily_budget_cents

    def record_usage(
        self,
        *,
        customer_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        operation: str = "query_expansion",
    ) -> CostRecord:
        """Record LLM token usage for a customer."""
        cost = (
            input_tokens * self._cost_per_input
            + output_tokens * self._cost_per_output
        )
        record = CostRecord(
            customer_id=customer_id,
            timestamp=time.time(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_cents=cost,
            model=model,
            operation=operation,
        )
        self._records.append(record)
        return record

    def _today_records(
        self, customer_id: str | None = None
    ) -> list[CostRecord]:
        """Filter records to today, optionally by customer."""
        today = datetime.now(UTC).date()
        result: list[CostRecord] = []
        for r in self._records:
            record_date = datetime.fromtimestamp(r.timestamp, tz=UTC).date()
            if record_date != today:
                continue
            if customer_id is not None and r.customer_id != customer_id:
                continue
            result.append(r)
        return result

    def check_budget(self, customer_id: str) -> CustomerBudgetStatus:
        """Check a customer's budget status for today."""
        budget = self._daily_budgets.get(
            customer_id, _DEFAULT_DAILY_BUDGET_CENTS
        )
        today_records = self._today_records(customer_id)
        spent = sum(r.estimated_cost_cents for r in today_records)
        remaining = max(0.0, budget - spent)
        return CustomerBudgetStatus(
            customer_id=customer_id,
            daily_budget_cents=budget,
            spent_today_cents=spent,
            remaining_cents=remaining,
            over_budget=spent >= budget,
            request_count_today=len(today_records),
        )

    def is_over_budget(self, customer_id: str) -> bool:
        """Convenience: return True if customer has exceeded daily budget."""
        return self.check_budget(customer_id).over_budget

    def get_dashboard(self) -> CostDashboard:
        """Aggregate cost dashboard for today."""
        today_records = self._today_records()

        total_spend = sum(r.estimated_cost_cents for r in today_records)
        total_tokens = sum(
            r.input_tokens + r.output_tokens for r in today_records
        )

        customer_breakdown: dict[str, float] = {}
        model_breakdown: dict[str, float] = {}
        for r in today_records:
            customer_breakdown[r.customer_id] = (
                customer_breakdown.get(r.customer_id, 0.0)
                + r.estimated_cost_cents
            )
            model_breakdown[r.model] = (
                model_breakdown.get(r.model, 0.0) + r.estimated_cost_cents
            )

        over_budget: list[str] = []
        for cid in customer_breakdown:
            if self.is_over_budget(cid):
                over_budget.append(cid)

        return CostDashboard(
            total_spend_cents=total_spend,
            total_tokens=total_tokens,
            customer_breakdown=customer_breakdown,
            model_breakdown=model_breakdown,
            over_budget_customers=over_budget,
        )
