import numpy as np
import pandas as pd

# Defaults so older assumption dicts (like in old tests) still work
DEFAULTS = {
    "gross_margin": 1.0,        # 1.0 = old behaviour (100% margin)
    "hire_growth_boost": 0.0,   # monthly growth boost per hire
}


def marketing_lift(marketing_pct, efficiency):
    """Diminishing returns: sqrt curve. 10% spend -> full `efficiency`,
    40% spend -> only 2x lift (not 4x)."""
    return efficiency * np.sqrt(max(marketing_pct, 0) / 0.10)


def run_simulation(assumptions, strategies):
    """Monte Carlo simulation of multiple possible business futures."""
    a = {**DEFAULTS, **assumptions}

    n = a["n_simulations"]
    months = a["horizon"]
    frames = []

    for i, strategy in enumerate(strategies):
        # Independent random stream per strategy (seeded by index, not dict equality)
        rng = np.random.default_rng(a["seed"] + i * 1009)

        revenue = np.full(n, a["monthly_revenue"], dtype=float)
        reserve = a["initial_cash"] * strategy["reserve_pct"]
        operating_cash = np.full(n, a["initial_cash"] - reserve, dtype=float)

        ever_short = np.zeros(n, dtype=bool)    # total cash < 0 (real shortfall)
        ever_breach = np.zeros(n, dtype=bool)   # operating cash < 0 (reserve is being used)
        cum_cf = np.zeros(n, dtype=float)

        lift = marketing_lift(strategy["marketing_pct"], a["marketing_efficiency"])
        boost = strategy["hires"] * a["hire_growth_boost"]
        fixed = a["fixed_costs"] + strategy["hires"] * a["salary_per_hire"]

        cols = {k: [] for k in
                ["revenue", "net_cash_flow", "operating_cash", "ending_cash",
                 "cumulative_cash_flow", "cash_shortfall", "reserve_breach"]}

        for _ in range(months):
            marketing_spend = revenue * strategy["marketing_pct"]

            growth = rng.normal(
                loc=a["base_growth"] + lift + boost,
                scale=a["growth_volatility"],
                size=n,
            )
            growth = np.clip(growth, -0.80, 1.50)
            revenue = np.maximum(0, revenue * (1 + growth))

            net_cf = revenue * a["gross_margin"] - fixed - marketing_spend
            operating_cash = operating_cash + net_cf
            cum_cf = cum_cf + net_cf

            total_cash = operating_cash + reserve
            ever_short |= total_cash < 0
            ever_breach |= operating_cash < 0

            cols["revenue"].append(revenue.copy())
            cols["net_cash_flow"].append(net_cf.copy())
            cols["operating_cash"].append(operating_cash.copy())
            cols["ending_cash"].append(total_cash.copy())
            cols["cumulative_cash_flow"].append(cum_cf.copy())
            cols["cash_shortfall"].append(ever_short.copy())
            cols["reserve_breach"].append(ever_breach.copy())

        df = pd.DataFrame({
            "strategy": strategy["name"],
            "simulation_id": np.tile(np.arange(n), months),
            "month": np.repeat(np.arange(1, months + 1), n),
            **{k: np.concatenate(v) for k, v in cols.items()},
        })
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def summarize_results(results):
    final = results[results["month"] == results["month"].max()]
    rows = []
    for name, g in final.groupby("strategy", sort=False):
        rows.append({
            "strategy": name,
            "survival_probability": (~g["cash_shortfall"]).mean(),
            "cash_shortfall_probability": g["cash_shortfall"].mean(),
            "reserve_breach_probability": g["reserve_breach"].mean(),
            "median_ending_cash": g["ending_cash"].median(),
            "p05_ending_cash": g["ending_cash"].quantile(0.05),
            "p95_ending_cash": g["ending_cash"].quantile(0.95),
            "median_ending_revenue": g["revenue"].median(),
            "median_cumulative_cash_flow": g["cumulative_cash_flow"].median(),
        })
    return pd.DataFrame(rows)


def build_fan_chart_data(results):
    return (
        results.groupby(["strategy", "month"], sort=False)["ending_cash"]
        .agg(median_cash="median",
             p05_cash=lambda x: x.quantile(0.05),
             p95_cash=lambda x: x.quantile(0.95))
        .reset_index()
    )


def run_growth_sensitivity(assumptions, strategy, growths=(-0.02, 0.0, 0.02, 0.04, 0.06)):
    rows = []
    for g in growths:
        test = {**assumptions, "base_growth": g}
        s = summarize_results(run_simulation(test, [strategy])).iloc[0]
        rows.append({
            "Monthly growth": f"{g:.0%}",
            "Median ending cash": s["median_ending_cash"],
            "Survival probability": s["survival_probability"],
        })
    return pd.DataFrame(rows)