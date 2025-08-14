import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Player Ranking", page_icon="⚽", layout="wide")
st.title("⚽ FPL Player Ranking — Weighted Score (DEFCONS incl.)")

# ---- Load your local file
DATA_PATH = Path("fpl2025cs.csv")
df = pd.read_csv(DATA_PATH)

# ---- Validate required columns
required_cols = [
    "Player","Squad","Pos",
    "xG_Expected","xAG_Expected","G+A","TklW_Tackles","Sh_Blocks","Int","Clr","Recov","Min_Playing"
]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Your file is missing required columns: {', '.join(missing)}")
    st.stop()

# ---- Fixed weights
weights = {
    "xG_Expected": 0.30, "xAG_Expected": 0.20, "G+A": 0.20,
    "TklW_Tackles": 0.05, "Sh_Blocks": 0.05, "Int": 0.05,
    "Clr": 0.05, "Recov": 0.05, "Min_Playing": 0.05,
}

# ---- Filters
with st.sidebar:
    st.header("Filters")
    pos_sel = st.multiselect("Pos", sorted(df["Pos"].dropna().unique()), default=None)
    squad_sel = st.multiselect("Squad", sorted(df["Squad"].dropna().unique()), default=None)

mask = pd.Series(True, index=df.index)
if pos_sel:
    mask &= df["Pos"].isin(pos_sel)
if squad_sel:
    mask &= df["Squad"].isin(squad_sel)
df_f = df.loc[mask].copy()
if df_f.empty:
    st.warning("No rows match your filters.")
    st.stop()

# ---- Min–Max normalize (higher is better)
def minmax(s):
    s = s.astype(float)
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng else pd.Series([0.5] * len(s), index=s.index)

norm = pd.DataFrame({c: minmax(df_f[c]) for c in weights})
df_f["Score"] = sum(norm[c] * w for c, w in weights.items())
df_f["Rank"] = df_f["Score"].rank(ascending=False, method="dense").astype(int)

# ---- Output
out = df_f[["Player","Squad","Pos","Score","Rank"]].sort_values("Score", ascending=False)
st.subheader("Results")
st.dataframe(out, use_container_width=True)

# ---- Download
st.download_button(
    "Download ranked CSV",
    data=out.to_csv(index=False).encode("utf-8"),
    file_name="player_ranking_minimal.csv",
    mime="text/csv",
)