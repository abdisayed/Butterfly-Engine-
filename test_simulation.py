import numpy as np
from simulation import run_simulation, summarize_results

BASE = {
    "initial_cash": 1000000, "monthly_revenue": 500000, "fixed_costs": 300000,
    "salary_per_hire": 60000, "base_growth": 0.02, "growth_volatility": 0.12,
    "marketing_efficiency": 0.06, "horizon": 3, "n_simulations": 20, "seed": 42,
}
STRAT = [{"name": "Balanced", "marketing_pct": 0.10, "hires": 1, "reserve_pct": 0.20}]


def test_simulation_runs():
    r = run_simulation(BASE, STRAT)
    assert len(r) == 60
    assert r["month"].max() == 3


def test_risk_probability_is_valid():
    p = summarize_results(run_simulation(BASE, STRAT)).iloc[0]["survival_probability"]
    assert 0 <= p <= 1


def test_same_seed_same_results():
    a = run_simulation(BASE, STRAT)
    b = run_simulation(BASE, STRAT)
    assert a.equals(b)


def test_survival_plus_shortfall_is_one():
    s = summarize_results(run_simulation(BASE, STRAT)).iloc[0]
    assert abs(s["survival_probability"] + s["cash_shortfall_probability"] - 1) < 1e-9


def test_shortfall_never_resets():
    r = run_simulation({**BASE, "horizon": 12}, STRAT).sort_values(["simulation_id", "month"])
    for _, g in r.groupby("simulation_id"):
        assert (np.diff(g["cash_shortfall"].astype(int)) >= 0).all()


def test_zero_volatility_matches_hand_calc():
    a = {**BASE, "growth_volatility": 0.0, "horizon": 1, "n_simulations": 5}
    r = run_simulation(a, STRAT).iloc[0]
    growth = 0.02 + 0.06            # marketing 10% -> lift = efficiency
    revenue = 500000 * (1 + growth)
    # NOTE: marketing spend uses revenue BEFORE growth
    cash_flow = revenue - (300000 + 60000) - 500000 * 0.10
    assert abs(r["revenue"] - revenue) < 1e-6
    assert abs(r["ending_cash"] - (1000000 + cash_flow)) < 1e-6


def test_marketing_has_diminishing_returns():
    from simulation import marketing_lift
    assert marketing_lift(0.40, 0.06) < 4 * marketing_lift(0.10, 0.06)