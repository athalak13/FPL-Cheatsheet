import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Player Ranking", page_icon="⚽", layout="wide")
st.title("⚽ Player Ranking — Weighted Score")

st.markdown(
    "Upload your data, adjust weights, and get an overall ranking. "
    "The app normalizes each metric so they’re comparable before weighting."
)

# ---- Data input
uploaded = st.file_uploader("/users/athalkhan/desktop/fpl2025cs.csv", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded)
else:
    st.info("/users/athalkhan/desktop/fpl2025cs.csv")
    st.stop()

# ---- Column mapping (lets you handle typos like Clt vs Clr)
st.sidebar.header("Column mapping")
def pick(label, options, default):
    return st.sidebar.selectbox(label, options, index=options.index(default) if default in options else 0)

cols = list(df.columns)

player_col     = pick("Player column", cols, "Player" if "Player" in cols else cols[0])
xg_col         = pick("xG column", cols, "xG_Expected")
xa_col         = pick("xA column (expected assists)", cols, "xAG_Expected")
ga_col         = pick("Actual G+A column", cols, "G+A")
tklw_col       = pick("Tackles Won column", cols, "TklW_Tackles")
blocks_col     = pick("Shot Blocks column", cols, "Sh_Blocks")
int_col        = pick("Interceptions column", cols, "Int")
clr_col        = pick("Clearances column", cols, "Clr")  # if you have 'Clt', just choose it here
recov_col      = pick("Recoveries column", cols, "Recov")
mins_col       = pick("Minutes Played column", cols, "Min_Playing")

# ---- Weights
st.sidebar.header("Weights (they’ll be normalized to sum to 1)")
w_xg     = st.sidebar.number_input("xG %", value=30.0, min_value=0.0, max_value=100.0, step=1.0)
w_xa     = st.sidebar.number_input("xA %", value=20.0, min_value=0.0, max_value=100.0, step=1.0)
w_ga     = st.sidebar.number_input("G+A %", value=20.0, min_value=0.0, max_value=100.0, step=1.0)
w_tklw   = st.sidebar.number_input("Tackles Won %", value=5.0,  min_value=0.0, max_value=100.0, step=1.0)
w_blocks = st.sidebar.number_input("Shot Blocks %", value=5.0,  min_value=0.0, max_value=100.0, step=1.0)
w_int    = st.sidebar.number_input("Interceptions %", value=5.0, min_value=0.0, max_value=100.0, step=1.0)
w_clr    = st.sidebar.number_input("Clearances %", value=5.0,   min_value=0.0, max_value=100.0, step=1.0)
w_recov  = st.sidebar.number_input("Recoveries %", value=5.0,   min_value=0.0, max_value=100.0, step=1.0)
w_mins   = st.sidebar.number_input("Minutes %", value=5.0,      min_value=0.0, max_value=100.0, step=1.0)

weights_raw = {
    xg_col: w_xg, xa_col: w_xa, ga_col: w_ga, tklw_col: w_tklw, blocks_col: w_blocks,
    int_col: w_int, clr_col: w_clr, recov_col: w_recov, mins_col: w_mins
}
total = sum(weights_raw.values())
if total == 0:
    st.error("All weights are zero. Increase at least one weight.")
    st.stop()
weights = {k: v / total for k, v in weights_raw.items()}  # normalize to sum=1

# ---- Normalization options
st.sidebar.header("Normalization")
norm_method = st.sidebar.radio("Method", ["Min-Max (0–1)", "Z-Score"], index=0)
higher_is_better_all = True  # if any metric should be reversed, toggle here or add a checkbox per metric

# (Optional) reverse some metrics example:
# reverse_cols = st.sidebar.multiselect("Reverse (lower is better)", options=list(weights.keys()), default=[])
reverse_cols = []  # by your spec, higher is better for all, including minutes

def minmax(s: pd.Series):
    rng = s.max() - s.min()
    if pd.isna(rng) or rng == 0:
        return pd.Series([0.5] * len(s), index=s.index)  # constant column -> neutral 0.5
    return (s - s.min()) / rng

def zscore(s: pd.Series):
    std = s.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series([0.0] * len(s), index=s.index)  # constant column -> neutral 0
    return (s - s.mean()) / std

df_norm = pd.DataFrame(index=df.index)
for col in weights.keys():
    series = df[col].astype(float)
    norm = minmax(series) if norm_method.startswith("Min-Max") else zscore(series)
    if col in reverse_cols:
        norm = 1 - norm if norm_method.startswith("Min-Max") else -norm
    df_norm[col] = norm

# ---- Weighted score & rank
score = sum(df_norm[c] * w for c, w in weights.items())
df_out = df.copy()
df_out["Score"] = score
df_out["Rank"] = df_out["Score"].rank(ascending=False, method="dense").astype(int)
df_out = df_out.sort_values(["Score"], ascending=False)

# ---- Display
st.subheader("Results")
st.caption("Sorted by Score (highest first)")
show_cols = [player_col, "Score", "Rank"] + list(weights.keys())
st.dataframe(df_out[show_cols], use_container_width=True)

# ---- Download
csv_bytes = df_out.to_csv(index=False).encode("utf-8")
st.download_button("Download ranked CSV", data=csv_bytes, file_name="player_ranking.csv", mime="text/csv")

# ---- Notes
with st.expander("How the score is calculated"):
    st.markdown(
        "- Each selected metric is normalized (either Min-Max to 0–1, or Z-Score).\n"
        "- Your weights are normalized to sum to 1.\n"
        "- Score = Σ (Normalized Metric × Weight).\n"
        "- Rank is assigned with the highest score = 1."
    )
