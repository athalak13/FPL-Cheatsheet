import pandas as pd
import io
import streamlit as st

st.set_page_config(page_title="Player Ranking", page_icon="⚽", layout="wide")
st.title("⚽ FPL Player Ranking — Weighted Score (Minimal)")

st.markdown("Upload a CSV with the required columns. Filter by Position and Team. "
            "The table only shows the final Score (and Rank).")

# ---- Data input
uploaded = st.file_uploader("Upload CSV", type=["csv"])
if not uploaded:
    st.stop()

df = pd.read_csv(uploaded)

# ---- Validate required columns
required_cols = [
    "Player","Squad","Pos",
    "xG_Expected","xAG_Expected","G+A","TklW_Tackles","Sh_Blocks","Int","Clr","Recov","Min_Playing"
]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Your file is missing required columns: {', '.join(missing)}")
    st.stop()

# ---- Fixed weights (sum to 1.0)
weights = {
    "xG_Expected":   0.30,
    "xAG_Expected":  0.20,
    "G+A":           0.20,
    "TklW_Tackles":  0.05,
    "Sh_Blocks":     0.05,
    "Int":           0.05,
    "Clr":           0.05,
    "Recov":         0.05,
    "Min_Playing":   0.05,
}

# ---- Filters (Position, Team only)
with st.sidebar:
    st.header("Filters")
    pos_opts = sorted(df["Pos"].dropna().unique().tolist())
    team_opts = sorted(df["Squad"].dropna().unique().tolist())

    pos_sel = st.multiselect("Pos", pos_opts, default=pos_opts)
    team_sel = st.multiselect("Squad", team_opts, default=team_opts)

# Apply filters
mask = df["Pos"].isin(pos_sel) & df["Squad"].isin(team_sel)
df_f = df.loc[mask].copy()

if df_f.empty:
    st.warning("No rows match your selected filters.")
    st.stop()

# ---- Min–Max normalization (higher is better for all)
def minmax_col(s: pd.Series):
    s = s.astype(float)
    rng = s.max() - s.min()
    if pd.isna(rng) or rng == 0:
        # constant column -> neutral value
        return pd.Series([0.5] * len(s), index=s.index)
    return (s - s.min()) / rng

norm_df = pd.DataFrame(index=df_f.index)
for col in weights.keys():
    norm_df[col] = minmax_col(df_f[col])

# ---- Weighted score & rank
df_f["Score"] = sum(norm_df[c] * w for c, w in weights.items())
df_f["Rank"] = df_f["Score"].rank(ascending=False, method="dense").astype(int)

# ---- Output (ONLY score + minimal identity fields)
out_cols = ["Player", "Squad", "Pos", "Score", "Rank"]
df_out = df_f[out_cols].sort_values(["Score"], ascending=False)

st.subheader("Results")
st.caption("Sorted by Score (highest first)")
st.dataframe(df_out, use_container_width=True)

# ---- Download
st.download_button(
    "Download ranked CSV",
    data=df_out.to_csv(index=False).encode("utf-8"),
    file_name="player_ranking_minimal.csv",
    mime="text/csv",
)

with st.expander("How Score is computed"):
    st.markdown(
        "- Fixed weights: xG 30%, xA 20%, G+A 20%, Tackles Won 5%, Shot Blocks 5%, Interceptions 5%, "
        "Clearances 5%, Recoveries 5%, Minutes 5%.\n"
        "- Metrics are min–max normalized to 0–1, then combined via weighted sum.\n"
        "- Rank is dense ranking with highest score = 1."
    )
