import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Task 2 – HC Model", layout="wide")

# -----------------------------
# Team bands (edit names if Motive uses different labels)
# -----------------------------
TEAMS = [
    {"team": "1-2",     "segment": "SMB",  "promo_to": "3-4",     "defaults": {"start": 10, "hires": 1,  "attr": 2.0, "promo": 5.0}},
    {"team": "3-4",     "segment": "SMB",  "promo_to": "5-9",     "defaults": {"start": 36, "hires": 20, "attr": 5.0, "promo": 30.0}},
    {"team": "5-9",     "segment": "SMB",  "promo_to": "10-19",   "defaults": {"start": 15, "hires": 15, "attr": 2.0, "promo": 20.0}},
    {"team": "10-19",   "segment": "CMRL", "promo_to": "20-29",   "defaults": {"start": 88, "hires": 4,  "attr": 3.0, "promo": 10.0}},
    {"team": "20-29",   "segment": "CMRL", "promo_to": "30-49",   "defaults": {"start": 44, "hires": 1,  "attr": 2.0, "promo": 10.0}},
    {"team": "30-49",   "segment": "CMRL", "promo_to": "50-99",   "defaults": {"start": 30, "hires": 1,  "attr": 2.0, "promo": 7.0}},
    {"team": "50-99",   "segment": "MM",   "promo_to": "100-149", "defaults": {"start": 27, "hires": 0,  "attr": 2.0, "promo": 6.0}},
    {"team": "100-149", "segment": "MM",   "promo_to": None,      "defaults": {"start": 10, "hires": 0,  "attr": 2.0, "promo": 0.0}},
]

TEAM_ORDER = [t["team"] for t in TEAMS]
TEAM_MAP = {t["team"]: t for t in TEAMS}

def months_index():
    # monthly from Jan 2025 to Dec 2026
    return pd.date_range(start="2025-01-01", end="2026-12-01", freq="MS")

def is_quarter_end(dt):
    return dt.month in (3, 6, 9, 12)

# -----------------------------
# Header
# -----------------------------
st.title("Task 2: Headcount Capacity Model (through end of 2026)")
st.caption(
    "Interactive model with promotions flowing upward by band. "
    "Use it to stress-test whether the organisation can support the Task 1 plan."
)

with st.expander("Assumptions (keep this panel-friendly)", expanded=False):
    st.markdown(
        """
- Granularity: **monthly** (Jan 2025 → Dec 2026)  
- Monthly order of operations: **Attrition → Hires → Promotions**  
- Promotions occur at **quarter-end** (Mar / Jun / Sep / Dec)  
- Promotions are true flow: headcount **moves up**, no double counting  
- Directional planning tool (productivity/ramp can be layered later)
        """.strip()
    )

st.divider()

# -----------------------------
# Inputs (per team)
# -----------------------------
st.subheader("Inputs (per team)")

inputs = {}

for band in TEAMS:
    team = band["team"]
    seg = band["segment"]
    promo_to = band["promo_to"] if band["promo_to"] else "n/a"
    d = band["defaults"]

    with st.expander(f"{seg} — Band {team}  (promotes to: {promo_to})", expanded=(seg == "SMB")):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            start = st.number_input(
                "Starting Headcount (HC)",
                min_value=0,
                value=int(d["start"]),
                step=1,
                key=f"{team}_start",
                help="Headcount at start of Jan 2025."
            )
        with c2:
            hires = st.number_input(
                "Monthly New Hires",
                min_value=0,
                value=int(d["hires"]),
                step=1,
                key=f"{team}_hires",
                help="Net hires added each month into this band."
            )
        with c3:
            attr = st.slider(
                "Monthly Attrition Rate (%)",
                min_value=0.0,
                max_value=15.0,
                value=float(d["attr"]),
                step=0.5,
                key=f"{team}_attr",
                help="Percent of this band leaving each month."
            )
        with c4:
            if band["promo_to"] is None:
                promo = 0.0
                st.number_input(
                    "Quarterly Promotion Rate (%)",
                    min_value=0.0,
                    max_value=0.0,
                    value=0.0,
                    step=1.0,
                    disabled=True,
                    key=f"{team}_promo",
                    help="Top band has no promotion destination."
                )
            else:
                promo = st.slider(
                    "Quarterly Promotion Rate (%)",
                    min_value=0.0,
                    max_value=40.0,
                    value=float(d["promo"]),
                    step=1.0,
                    key=f"{team}_promo",
                    help=f"At quarter-end, % of band {team} promoted up to {promo_to}."
                )

        inputs[team] = {
            "segment": seg,
            "starting": float(start),
            "hires": float(hires),
            "attr": float(attr) / 100.0,
            "promo": float(promo) / 100.0,
            "promo_to": band["promo_to"],
        }

st.divider()

# -----------------------------
# Simulation
# -----------------------------
def simulate():
    dates = months_index()

    hc = {t: inputs[t]["starting"] for t in TEAM_ORDER}

    rows = []
    promo_rows = []  # track quarterly flows

    for dt in dates:
        # 1) Attrition
        for t in TEAM_ORDER:
            hc[t] = hc[t] * (1.0 - inputs[t]["attr"])

        # 2) Hires
        for t in TEAM_ORDER:
            hc[t] = hc[t] + inputs[t]["hires"]

        # 3) Promotions at quarter end
        if is_quarter_end(dt):
            moves = {t: 0.0 for t in TEAM_ORDER}
            for t in TEAM_ORDER:
                to_team = inputs[t]["promo_to"]
                if to_team is None:
                    continue
                moves[t] = hc[t] * inputs[t]["promo"]

            # apply moves
            for t in TEAM_ORDER:
                to_team = inputs[t]["promo_to"]
                if to_team is None:
                    continue
                amt = moves[t]
                hc[t] -= amt
                hc[to_team] += amt

                promo_rows.append({
                    "Quarter End": dt.strftime("%Y-%m"),
                    "From Band": t,
                    "To Band": to_team,
                    "Promoted HC": round(amt, 1),
                })

        # record
        row = {"Month": dt}
        for t in TEAM_ORDER:
            row[t] = max(0.0, hc[t])
        row["Total"] = sum(row[t] for t in TEAM_ORDER)
        rows.append(row)

    df = pd.DataFrame(rows)
    promo_df = pd.DataFrame(promo_rows) if promo_rows else pd.DataFrame(columns=["Quarter End", "From Band", "To Band", "Promoted HC"])
    return df, promo_df

df, promo_df = simulate()

# -----------------------------
# Outputs
# -----------------------------
st.subheader("Outputs")

k1, k2, k3 = st.columns(3)
k1.metric("Projected Total HC (Dec 2026)", f"{df.iloc[-1]['Total']:,.0f}")
k2.metric("Start Total HC (Jan 2025)", f"{df.iloc[0]['Total']:,.0f}")
k3.metric("Net Change", f"{(df.iloc[-1]['Total'] - df.iloc[0]['Total']):,.0f}")

st.markdown("### Aggregate total headcount trend")
chart_total = (
    alt.Chart(df)
    .mark_line(point=False)
    .encode(
        x=alt.X("Month:T", title="Month"),
        y=alt.Y("Total:Q", title="Total Headcount (All bands)"),
        tooltip=[alt.Tooltip("Month:T"), alt.Tooltip("Total:Q", format=",.0f")]
    )
    .properties(height=260)
)
st.altair_chart(chart_total, use_container_width=True)

st.markdown("### Individual team projections (by band)")
long_df = df.melt(id_vars=["Month"], value_vars=TEAM_ORDER, var_name="Band", value_name="Headcount")

chart_bands = (
    alt.Chart(long_df)
    .mark_line()
    .encode(
        x=alt.X("Month:T", title="Month"),
        y=alt.Y("Headcount:Q", title="Headcount (per band)"),
        color=alt.Color("Band:N", title="Band"),
        tooltip=[alt.Tooltip("Month:T"), "Band:N", alt.Tooltip("Headcount:Q", format=",.0f")]
    )
    .properties(height=360)
)
st.altair_chart(chart_bands, use_container_width=True)

st.markdown("### Promotion flow (quarter-end movements)")
st.caption("This table explicitly shows upward movement between bands at each quarter end.")

if promo_df.empty:
    st.info("No promotions recorded (all promotion rates are 0%).")
else:
    st.dataframe(promo_df, use_container_width=True, hide_index=True)

with st.expander("Monthly headcount table (appendix)"):
    df_show = df.copy()
    df_show["Month"] = df_show["Month"].dt.strftime("%Y-%m")
    st.dataframe(df_show.round(2), use_container_width=True, hide_index=True)
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Task 2 – Capacity Model", layout="centered")

# ---------------------------
# Context
# ---------------------------
st.title("Task 2: Capacity Stress Test")
st.caption(
    "This model tests whether the organisation has enough account management "
    "capacity to support the Task 1 growth and retention strategy."
)

st.markdown(
    """
This is a **directional model**, not a forecast.
It is designed to highlight **capacity constraints and risk**, not precision.
"""
)

st.divider()

# ---------------------------
# Inputs
# ---------------------------
st.subheader("Assumptions")

starting_headcount = st.number_input(
    "Starting Account Management headcount",
    min_value=0,
    value=100,
    step=5
)

monthly_hires = st.number_input(
    "Monthly hires",
    min_value=0,
    value=4,
    step=1
)

monthly_attrition = st.slider(
    "Monthly attrition (%)",
    min_value=0.0,
    max_value=10.0,
    value=2.0,
    step=0.5
)

st.divider()

# ---------------------------
# Model
# ---------------------------
months = pd.date_range(start="2025-01-01", end="2026-12-01", freq="MS")

headcount = []
hc = starting_headcount

for month in months:
    hc = hc * (1 - monthly_attrition / 100)
    hc = hc + monthly_hires
    headcount.append(round(hc, 1))

df = pd.DataFrame({
    "Month": months,
    "Headcount": headcount
})

# ---------------------------
# Output
# ---------------------------
st.subheader("Projected Capacity Over Time")

chart = (
    alt.Chart(df)
    .mark_line(point=True)
    .encode(
        x=alt.X("Month:T", title="Month"),
        y=alt.Y("Headcount:Q", title="Total Account Management Headcount"),
        tooltip=["Month:T", "Headcount:Q"]
    )
)

st.altair_chart(chart, use_container_width=True)

st.markdown(
    """
**How to interpret this:**
- If growth expectations increase without increasing hiring, capacity becomes constrained  
- Capacity pressure increases churn risk and limits expansion execution  
- This highlights where investment in people is required to support strategy
"""
)

