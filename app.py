import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from simulation import (
    run_simulation, summarize_results, build_fan_chart_data, run_growth_sensitivity,
)
from db import init_db, save_run, load_recent_runs

st.set_page_config(page_title="Butterfly Engine", page_icon="🦋", layout="wide")

# ---------------- THEME ----------------
INK, PANEL, LINE = "#0B1020", "#131B33", "#25305A"
TEXT, MUTED = "#E8ECF8", "#8D99C2"
MORPHO, AQUA, VIOLET, AMBER, ROSE = "#4F8CFF", "#2DD4BF", "#A78BFA", "#F5A524", "#FB7185"
COLORS = {"Conservative": AQUA, "Growth": VIOLET, "Balanced": AMBER}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700&family=Manrope:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Manrope', sans-serif; }}
h1, h2, h3, h4 {{ font-family: 'Sora', sans-serif !important; letter-spacing: -0.01em; }}
.stApp {{ background:
  radial-gradient(900px 500px at 85% -10%, rgba(79,140,255,.18), transparent 60%),
  radial-gradient(700px 400px at -5% 10%, rgba(167,139,250,.14), transparent 60%),
  {INK}; color: {TEXT}; }}
[data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid {LINE}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2rem; max-width: 1250px; }}

.hero {{ display:flex; gap:28px; align-items:center; padding:28px 32px; border-radius:22px;
  background: linear-gradient(120deg, rgba(79,140,255,.16), rgba(167,139,250,.10) 55%, rgba(45,212,191,.10));
  border:1px solid {LINE}; margin-bottom:8px; }}
.hero h1 {{ font-size:2.6rem; margin:0; line-height:1.1; }}
.hero p {{ color:{MUTED}; margin:.4rem 0 0; font-size:1.05rem; max-width:560px; }}
.hero svg {{ flex:none; filter: drop-shadow(0 0 22px rgba(79,140,255,.55)); }}

.kpi {{ background:{PANEL}; border:1px solid {LINE}; border-radius:16px; padding:18px 20px; height:100%; }}
.kpi .label {{ color:{MUTED}; font-size:.85rem; }}
.kpi .value {{ font-family:'Sora'; font-size:1.55rem; font-weight:700; margin-top:4px; }}
.kpi .sub {{ font-size:.85rem; margin-top:2px; }}

.verdict {{ border-radius:16px; padding:18px 22px; border:1px solid {LINE};
  background: linear-gradient(90deg, rgba(79,140,255,.14), rgba(19,27,51,.6)); margin:14px 0 4px; line-height:1.6; }}

.scard {{ border-radius:16px; padding:6px 16px 2px; background:{PANEL}; border:1px solid {LINE}; border-top-width:4px; }}
.scard h3 {{ margin:10px 0 0; font-size:1.15rem; }}

div[data-testid="stButton"] > button[kind="primary"] {{
  background: linear-gradient(90deg, {MORPHO}, {VIOLET}); border:0; color:white; font-weight:700;
  padding:.8rem 1rem; border-radius:14px; font-family:'Sora'; box-shadow:0 8px 30px rgba(79,140,255,.35); }}
div[data-testid="stButton"] > button[kind="primary"]:hover {{ filter:brightness(1.1); }}
div[data-testid="stButton"] > button:focus-visible {{ outline:2px solid {AQUA}; }}
[data-testid="stDataFrame"] {{ border:1px solid {LINE}; border-radius:12px; }}
hr {{ border-color:{LINE}; }}
@media (max-width:700px) {{ .hero {{ flex-direction:column; text-align:center; }} .hero h1 {{ font-size:2rem; }} }}
</style>
""", unsafe_allow_html=True)

BUTTERFLY = f"""
<svg width="96" height="96" viewBox="0 0 100 100" aria-hidden="true">
 <defs><linearGradient id="w" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{MORPHO}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>
 <path d="M50 48 C30 10 5 14 8 38 C10 56 30 58 50 52Z" fill="url(#w)"/>
 <path d="M50 48 C70 10 95 14 92 38 C90 56 70 58 50 52Z" fill="url(#w)" opacity=".85"/>
 <path d="M50 54 C32 56 14 66 22 84 C32 92 46 76 50 58Z" fill="{AQUA}" opacity=".9"/>
 <path d="M50 54 C68 56 86 66 78 84 C68 92 54 76 50 58Z" fill="{AQUA}" opacity=".75"/>
 <rect x="48.5" y="36" width="3" height="40" rx="1.5" fill="{TEXT}"/>
</svg>"""

st.markdown(f"""
<div class="hero">{BUTTERFLY}
 <div><h1>Butterfly Engine</h1>
 <p>One small decision, thousands of possible futures. Simulate your strategies and see which one holds up.</p></div>
</div>""", unsafe_allow_html=True)
st.caption("Monte Carlo business simulation · Illustrative assumptions, not guaranteed forecasts")


def style(fig, height=380):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope", color=TEXT), height=height,
        margin=dict(l=10, r=10, t=50, b=10), title_font=dict(family="Sora", size=16),
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_xaxes(gridcolor=LINE, zeroline=False)
    fig.update_yaxes(gridcolor=LINE, zeroline=False)
    return fig


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def inr(x):
    return f"₹{x:,.0f}"


def kpi(label, value, sub="", color=TEXT):
    return (f'<div class="kpi"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="sub" style="color:{color}">{sub}</div></div>')


# ---------------- SIDEBAR ----------------
sb = st.sidebar
sb.header("⚙️ Simulation settings")
initial_cash = sb.number_input("Starting cash (₹)", min_value=10000, value=1000000, step=50000)
monthly_revenue = sb.number_input("Monthly revenue (₹)", min_value=1000, value=500000, step=25000)
fixed_costs = sb.number_input("Monthly fixed costs (₹)", min_value=0, value=300000, step=10000)
salary_per_hire = sb.number_input("Monthly cost per hire (₹)", min_value=0, value=60000, step=5000)
gross_margin_pct = sb.slider("Gross margin (%)", 20, 100, 80, 5,
                             help="Share of revenue left after cost of goods sold")
growth_pct = sb.slider("Baseline monthly growth (%)", -10.0, 20.0, 2.0, 0.5)
volatility_pct = sb.slider("Monthly growth uncertainty (%)", 1.0, 50.0, 12.0, 0.5)
marketing_eff_pct = sb.slider("Marketing lift at 10% spend (%)", 0.0, 20.0, 6.0, 0.5,
                              help="Returns diminish: doubling spend does not double the lift")
hire_boost_pct = sb.slider("Growth boost per hire (%/month)", 0.0, 3.0, 0.5, 0.1,
                           help="Monthly growth added by each hire")
horizon_in = sb.slider("Forecast horizon (months)", 3, 36, 12)
n_in = sb.select_slider("Simulated futures", options=[100, 250, 500, 1000, 2500, 5000], value=1000)
seed = sb.number_input("Random seed", min_value=0, value=42, step=1)

assumptions_in = {
    "initial_cash": float(initial_cash), "monthly_revenue": float(monthly_revenue),
    "fixed_costs": float(fixed_costs), "salary_per_hire": float(salary_per_hire),
    "gross_margin": gross_margin_pct / 100, "base_growth": growth_pct / 100,
    "growth_volatility": volatility_pct / 100, "marketing_efficiency": marketing_eff_pct / 100,
    "hire_growth_boost": hire_boost_pct / 100, "horizon": int(horizon_in),
    "n_simulations": int(n_in), "seed": int(seed),
}

# ---------------- STRATEGIES ----------------
st.header("1. Design your strategies")
presets = [("Conservative", "🛡️", 5, 0, 30), ("Growth", "🚀", 15, 2, 10), ("Balanced", "⚖️", 10, 1, 20)]
strategies_in = []
for col, (name, icon, m, h, r) in zip(st.columns(3), presets):
    with col:
        st.markdown(f'<div class="scard" style="border-top-color:{COLORS[name]}"><h3>{icon} {name}</h3></div>',
                    unsafe_allow_html=True)
        mk = st.slider("Marketing spend (%)", 0, 30, m, key=f"{name}_m")
        hr = st.slider("New hires", 0, 10, h, key=f"{name}_h")
        rs = st.slider("Protected cash reserve (%)", 0, 70, r, 5, key=f"{name}_r")
        strategies_in.append({"name": name, "marketing_pct": mk / 100, "hires": hr, "reserve_pct": rs / 100})

# ---------------- RUN ----------------
if st.button("🦋 Simulate possible futures", type="primary", width="stretch"):
    with st.spinner("Simulating possible futures..."):
        res = run_simulation(assumptions_in, strategies_in)
        st.session_state.update(
            results=res,
            summary=summarize_results(res),
            assumptions=assumptions_in,
            strategies=strategies_in,
            sensitivity=run_growth_sensitivity(
                assumptions_in, next(s for s in strategies_in if s["name"] == "Balanced")),
            history=None,
        )

if "results" not in st.session_state:
    st.info("Set your assumptions in the sidebar, choose your strategies, then click Simulate.")
    st.stop()

# Always use the saved values, not the live sliders
results = st.session_state["results"]
summary = st.session_state["summary"]
A = st.session_state["assumptions"]
horizon = A["horizon"]

if A != assumptions_in or st.session_state["strategies"] != strategies_in:
    st.warning("Settings have changed. The results below reflect the previous settings. Run the simulation again to update them.")

# ---------------- SNAPSHOT ----------------
st.divider()
st.header("2. Executive snapshot")
safest = summary.loc[summary["survival_probability"].idxmax()]
richest = summary.loc[summary["median_ending_cash"].idxmax()]
riskiest = summary.loc[summary["survival_probability"].idxmin()]

cards = [
    kpi("Simulated futures", f"{A['n_simulations']:,}", f"{horizon} months each"),
    kpi("Safest strategy", safest["strategy"], f"{safest['survival_probability']:.1%} survival",
        COLORS.get(safest["strategy"], AQUA)),
    kpi("Highest median cash", richest["strategy"], inr(richest["median_ending_cash"]),
        COLORS.get(richest["strategy"], AQUA)),
    kpi("Most at risk", riskiest["strategy"], f"{riskiest['cash_shortfall_probability']:.1%} shortfall", ROSE),
]
for col, html in zip(st.columns(4), cards):
    col.markdown(html, unsafe_allow_html=True)

if safest["strategy"] == richest["strategy"]:
    msg = (f"<b>{safest['strategy']}</b> leads on both counts: highest survival and highest median cash "
           f"({inr(richest['median_ending_cash'])}).")
else:
    msg = (f"<b>{safest['strategy']}</b> is the safest ({safest['survival_probability']:.1%} survival), "
           f"but <b>{richest['strategy']}</b> has the higher median cash ({inr(richest['median_ending_cash'])}). "
           f"This is a risk-versus-reward trade-off.")
st.markdown(f'<div class="verdict">🦋 {msg}</div>', unsafe_allow_html=True)

# ---------------- COMPARE ----------------
st.header("3. Compare strategies")
d = summary.copy()
for c in ["survival_probability", "cash_shortfall_probability", "reserve_breach_probability"]:
    d[c] = d[c].map("{:.1%}".format)
for c in ["median_ending_cash", "p05_ending_cash", "p95_ending_cash",
          "median_ending_revenue", "median_cumulative_cash_flow"]:
    d[c] = d[c].map(inr)
d = d.rename(columns={
    "strategy": "Strategy", "survival_probability": "Survival (cash never < 0)",
    "cash_shortfall_probability": "Cash shortfall risk",
    "reserve_breach_probability": "Reserve breach risk",
    "median_ending_cash": "Median ending cash", "p05_ending_cash": "5th percentile cash",
    "p95_ending_cash": "95th percentile cash", "median_ending_revenue": "Median monthly revenue",
    "median_cumulative_cash_flow": "Median cumulative cash flow",
})
st.dataframe(d, width="stretch", hide_index=True)
st.caption("Shortfall = total cash (including the reserve) falls below zero. Reserve breach = operating cash runs out and the reserve starts being used.")

# ---------------- RISK ----------------
st.header("4. Risk analysis")
left, right = st.columns(2)
with left:
    long = summary.melt(id_vars="strategy",
                        value_vars=["survival_probability", "reserve_breach_probability"],
                        var_name="metric", value_name="p")
    long["metric"] = long["metric"].map({"survival_probability": "Survival",
                                         "reserve_breach_probability": "Reserve breach"})
    fig = px.bar(long, x="strategy", y="p", color="metric", barmode="group",
                 color_discrete_map={"Survival": AQUA, "Reserve breach": AMBER},
                 title="Survival vs reserve breach", labels={"p": "Probability", "strategy": ""})
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(style(fig), width="stretch")
with right:
    fig = px.box(results[results["month"] == horizon], x="strategy", y="ending_cash",
                 color="strategy", color_discrete_map=COLORS,
                 title="Distribution of ending cash", labels={"ending_cash": "Ending cash (₹)", "strategy": ""})
    fig.update_layout(showlegend=False)
    st.plotly_chart(style(fig), width="stretch")

# ---------------- FAN ----------------
st.header("5. Butterfly view: many possible futures")
fan = build_fan_chart_data(results)
fig = go.Figure()
for name in fan["strategy"].unique():
    f = fan[fan["strategy"] == name].sort_values("month")
    col = COLORS.get(name, MUTED)
    fig.add_trace(go.Scatter(x=f["month"], y=f["p95_cash"], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip", legendgroup=name))
    fig.add_trace(go.Scatter(x=f["month"], y=f["p05_cash"], mode="lines", fill="tonexty",
                             fillcolor=rgba(col, 0.16), line=dict(width=0), hoverinfo="skip",
                             name=f"{name} 5–95%", legendgroup=name))
    fig.add_trace(go.Scatter(x=f["month"], y=f["median_cash"], mode="lines+markers",
                             line=dict(color=col, width=3), name=f"{name} median", legendgroup=name))
fig.add_hline(y=0, line_dash="dot", line_color=ROSE, annotation_text="Cash = 0")
fig.update_layout(title="Cash trajectories: median and 5th–95th percentile", hovermode="x unified",
                  xaxis_title="Month", yaxis_title="Cash balance (₹)")
st.plotly_chart(style(fig, 460), width="stretch")
st.caption("Shaded band = 5th–95th percentile outcomes. These are simulation ranges, not guarantees.")

# ---------------- SENSITIVITY ----------------
st.header("6. Sensitivity: Balanced strategy")
st.write("How much do the results change if baseline monthly growth is different? All other assumptions stay fixed.")
sens = st.session_state["sensitivity"]
left, right = st.columns(2)
with left:
    fig = px.line(sens, x="Monthly growth", y="Median ending cash", markers=True,
                  title="Growth vs median ending cash")
    fig.update_traces(line=dict(color=MORPHO, width=3), marker=dict(size=9))
    st.plotly_chart(style(fig, 340), width="stretch")
with right:
    fig = px.bar(sens, x="Monthly growth", y="Survival probability", title="Growth vs survival probability")
    fig.update_traces(marker_color=VIOLET)
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(style(fig, 340), width="stretch")

# ---------------- HISTORY ----------------
st.header("7. Experiment history")
b1, b2 = st.columns(2)
if b1.button("💾 Save experiment to MySQL", width="stretch"):
    try:
        init_db()
        rid = save_run(A, st.session_state["strategies"], summary)
        st.success(f"Experiment #{rid} saved.")
    except Exception as exc:
        st.error(f"Could not save the experiment. Check your .env credentials and MySQL server. Details: {exc}")

if b2.button("🔄 Load recent experiments", width="stretch"):
    try:
        init_db()
        st.session_state["history"] = load_recent_runs()
    except Exception as exc:
        st.error(f"Could not load history: {exc}")

hist = st.session_state.get("history")
if isinstance(hist, pd.DataFrame):
    if hist.empty:
        st.info("No saved experiments yet.")
    else:
        st.dataframe(hist, width="stretch", hide_index=True)

st.divider()
st.caption("Butterfly Engine · Educational decision-support prototype. Marketing lift, hiring boost and other "
           "parameters are illustrative assumptions, not learned causal effects. Not financial advice.")