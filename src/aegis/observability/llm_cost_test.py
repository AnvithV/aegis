"""Tests for LLM cost monitoring."""

from __future__ import annotations

from aegis.observability.llm_cost import CostRecord, LlmCostMonitor


def test_record_usage() -> None:
    monitor = LlmCostMonitor()
    record = monitor.record_usage(
        customer_id="cust-1",
        input_tokens=1000,
        output_tokens=200,
        model="claude-sonnet-4-20250514",
    )
    assert isinstance(record, CostRecord)
    expected_cost = 1000 * 0.0003 + 200 * 0.0015
    assert abs(record.estimated_cost_cents - expected_cost) < 1e-6


def test_check_budget_within() -> None:
    monitor = LlmCostMonitor()
    monitor.set_budget("cust-1", 1000.0)
    monitor.record_usage(
        customer_id="cust-1",
        input_tokens=100,
        output_tokens=50,
        model="test-model",
    )
    status = monitor.check_budget("cust-1")
    assert status.over_budget is False
    assert status.remaining_cents > 0


def test_check_budget_exceeded() -> None:
    monitor = LlmCostMonitor()
    monitor.set_budget("cust-1", 1.0)  # Very low budget: 1 cent
    monitor.record_usage(
        customer_id="cust-1",
        input_tokens=10000,
        output_tokens=5000,
        model="test-model",
    )
    status = monitor.check_budget("cust-1")
    assert status.over_budget is True


def test_is_over_budget() -> None:
    monitor = LlmCostMonitor()
    monitor.set_budget("cust-1", 1.0)
    monitor.record_usage(
        customer_id="cust-1",
        input_tokens=10000,
        output_tokens=5000,
        model="test-model",
    )
    assert monitor.is_over_budget("cust-1") is True


def test_dashboard() -> None:
    monitor = LlmCostMonitor()
    monitor.record_usage(
        customer_id="cust-1",
        input_tokens=100,
        output_tokens=50,
        model="model-a",
    )
    monitor.record_usage(
        customer_id="cust-2",
        input_tokens=200,
        output_tokens=100,
        model="model-b",
    )
    dashboard = monitor.get_dashboard()
    assert "cust-1" in dashboard.customer_breakdown
    assert "cust-2" in dashboard.customer_breakdown
    assert dashboard.total_tokens == 450


def test_over_budget_customers_listed() -> None:
    monitor = LlmCostMonitor()
    monitor.set_budget("cust-1", 0.001)  # Tiny budget
    monitor.record_usage(
        customer_id="cust-1",
        input_tokens=10000,
        output_tokens=5000,
        model="test-model",
    )
    monitor.record_usage(
        customer_id="cust-2",
        input_tokens=10,
        output_tokens=5,
        model="test-model",
    )
    dashboard = monitor.get_dashboard()
    assert "cust-1" in dashboard.over_budget_customers


def test_default_budget() -> None:
    monitor = LlmCostMonitor()
    status = monitor.check_budget("no-budget-set")
    assert status.daily_budget_cents == 1000.0


def test_cost_record_model() -> None:
    record = CostRecord(
        customer_id="cust-1",
        timestamp=1000000.0,
        input_tokens=500,
        output_tokens=100,
        estimated_cost_cents=0.3,
        model="test-model",
        operation="query_expansion",
    )
    data = record.model_dump_json()
    assert "cust-1" in data
