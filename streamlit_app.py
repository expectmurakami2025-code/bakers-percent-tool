import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="ベーカーズパーセント変換ツール", page_icon="🥖", layout="wide")

st.title("🥖 ベーカーズパーセント 変換 & スケーリング ツール")
st.caption("粉を100%として、重さ⇄ベーカーズ%を相互変換。さらに任意重量・個数にスケーリングできます。")

# ===== サイドバー =====
with st.sidebar:
    st.header("モード")
    mode = st.radio(
        "計算モードを選択",
        options=["重さ → ベーカーズ%", "ベーカーズ% → 重さ"],
        help="・重さ → ベーカーズ%：各材料の重さから%を計算\n・ベーカーズ% → 重さ：%から重さを計算"
    )
    st.divider()
    st.header("粉（Flour）扱いの材料")
    st.caption("複数の粉（強力粉・全粒粉など）を合算して100%にします。")
    flour_keywords = st.text_input(
        "名称にこれらの語が含まれたら粉として扱う（カンマ区切り）",
        value="強力粉, 薄力粉, 準強力粉, ライ麦, 全粒粉, 中力粉, Bread Flour, Flour, Rye, Whole Wheat"
    )
    flour_words = [w.strip().lower() for w in flour_keywords.split(",") if w.strip()]
    st.divider()
    st.header("プリセット例")
    preset = st.selectbox(
        "レシピ例を読み込み",
        ["（選択しない）", "食パン 基本", "ハード系（高加水）", "ピザ生地", "菓子パン（甘め）"]
    )

def load_preset(name: str):
    if name == "食パン 基本":
        return [
            {"材料":"強力粉","重さ(g)":300.0,"ベーカーズ%":np.nan},
            {"材料":"水","重さ(g)":180.0,"ベーカーズ%":np.nan},
            {"材料":"塩","重さ(g)":6.0,"ベーカーズ%":np.nan},
            {"材料":"砂糖","重さ(g)":15.0,"ベーカーズ%":np.nan},
            {"材料":"ドライイースト","重さ(g)":3.0,"ベーカーズ%":np.nan},
            {"材料":"バター","重さ(g)":15.0,"ベーカーズ%":np.nan},
        ]
    if name == "ハード系（高加水）":
        return [
            {"材料":"準強力粉","重さ(g)":300.0,"ベーカーズ%":np.nan},
            {"材料":"水","重さ(g)":225.0,"ベーカーズ%":np.nan},
            {"材料":"塩","重さ(g)":6.0,"ベーカーズ%":np.nan},
            {"材料":"インスタントドライイースト","重さ(g)":1.5,"ベーカーズ%":np.nan},
        ]
    if name == "ピザ生地":
        return [
            {"材料":"強力粉","重さ(g)":250.0,"ベーカーズ%":np.nan},
            {"材料":"水","重さ(g)":160.0,"ベーカーズ%":np.nan},
            {"材料":"塩","重さ(g)":5.0,"ベーカーズ%":np.nan},
            {"材料":"オリーブオイル","重さ(g)":10.0,"ベーカーズ%":np.nan},
            {"材料":"ドライイースト","重さ(g)":2.5,"ベーカーズ%":np.nan},
        ]
    if name == "菓子パン（甘め）":
        return [
            {"材料":"強力粉","重さ(g)":250.0,"ベーカーズ%":np.nan},
            {"材料":"牛乳","重さ(g)":160.0,"ベーカーズ%":np.nan},
            {"材料":"砂糖","重さ(g)":40.0,"ベーカーズ%":np.nan},
            {"材料":"塩","重さ(g)":4.0,"ベーカーズ%":np.nan},
            {"材料":"卵","重さ(g)":50.0,"ベーカーズ%":np.nan},
            {"材料":"バター","重さ(g)":25.0,"ベーカーズ%":np.nan},
            {"材料":"ドライイースト","重さ(g)":4.0,"ベーカーズ%":np.nan},
        ]
    return [
        {"材料":"強力粉","重さ(g)":300.0,"ベーカーズ%":np.nan},
        {"材料":"水","重さ(g)":180.0,"ベーカーズ%":np.nan},
        {"材料":"塩","重さ(g)":6.0,"ベーカーズ%":np.nan},
        {"材料":"ドライイースト","重さ(g)":3.0,"ベーカーズ%":np.nan},
    ]

# ===== 初期データ =====
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(load_preset("（選択しない）"))

if preset != "（選択しない）" and st.button("このプリセットを読み込む", type="primary"):
    st.session_state.df = pd.DataFrame(load_preset(preset))

st.subheader("材料表を編集")
st.caption("行の追加・削除、重量や%の入力ができます。名称に「粉」相当の語を含む行が粉として集計されます。")
edited_df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "材料": st.column_config.TextColumn("材料", width="medium", help="材料名"),
        "重さ(g)": st.column_config.NumberColumn("重さ(g)", min_value=0.0, step=1.0, help="グラム単位で入力"),
        "ベーカーズ%": st.column_config.NumberColumn("ベーカーズ%", min_value=0.0, step=0.1, help="粉=100%に対する割合")
    }
)
st.session_state.df = edited_df.copy()

# ===== ユーティリティ =====
def is_flour(name: str) -> bool:
    s = (name or "").lower()
    return any(w in s for w in flour_words)

def compute_from_weights(df: pd.DataFrame):
    df = df.copy()
    flour_weight = df.loc[df["材料"].apply(is_flour), "重さ(g)"].fillna(0).sum()
    if flour_weight <= 0:
        st.warning("粉として扱う行の『重さ(g)』合計が0です。粉の重さを入力してください。")
        flour_weight = np.nan
    df["ベーカーズ%"] = (df["重さ(g)"] / flour_weight * 100.0).round(2)
    total_dough = df["重さ(g)"].fillna(0).sum()
    hydration = df.loc[df["材料"].str.contains("水|water|牛乳|milk|卵|egg", case=False, na=False), "重さ(g)"].sum()
    return df, flour_weight, total_dough, hydration

def compute_from_bakers(df: pd.DataFrame, flour_weight_input: float = None, target_total: float = None):
    df = df.copy()
    flour_mask = df["材料"].apply(is_flour)
    flour_percent_sum = df.loc[flour_mask, "ベーカーズ%"].fillna(0).sum()
    if flour_percent_sum == 0:
        if flour_mask.any():
            first_flour_idx = df.index[flour_mask][0]
            df.loc[first_flour_idx, "ベーカーズ%"] = 100.0

    percent_sum = df["ベーカーズ%"].fillna(0).sum()
    if flour_weight_input and flour_weight_input > 0:
        flour_weight = flour_weight_input
    elif target_total and percent_sum > 0:
        flour_weight = target_total * (100.0 / percent_sum)
    else:
        flour_weight = 300.0  # デフォルト

    df["重さ(g)"] = (df["ベーカーズ%"] / 100.0 * flour_weight).round(1)
    total_dough = df["重さ(g)"].fillna(0).sum()
    hydration = df.loc[df["材料"].str.contains("水|water|牛乳|milk|卵|egg", case=False, na=False), "重さ(g)"].sum()
    return df, flour_weight, total_dough, hydration

# ===== 計算設定 =====
st.subheader("計算設定")
colA, colB, colC = st.columns(3)
with colA:
    flour_weight_input = st.number_input("粉の合計重量を指定（任意）[g]", min_value=0.0, value=0.0, step=10.0, help="ベーカーズ%→重さ で利用。0なら自動。")
with colB:
    target_total = st.number_input("総生地重量（完成生地の重さ）を指定（任意）[g]", min_value=0.0, value=0.0, step=10.0, help="ベーカーズ%→重さ で利用。0なら未指定。")
with colC:
    st.write("　")
    calc_btn = st.button("計算する", type="primary", use_container_width=True)

if calc_btn or True:
    if mode == "重さ → ベーカーズ%":
        out_df, flour_w, total_w, hydration_w = compute_from_weights(st.session_state.df)
    else:
        fw = flour_weight_input if flour_weight_input > 0 else None
        tt = target_total if target_total > 0 else None
        out_df, flour_w, total_w, hydration_w = compute_from_bakers(st.session_state.df, fw, tt)

    st.subheader("結果")
    st.dataframe(out_df, use_container_width=True)

    st.markdown("### サマリー")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("粉の合計（g）", f"{flour_w if pd.notna(flour_w) else '-'}")
    with col2:
        st.metric("総生地重量（g）", f"{total_w:.1f}")
    with col3:
        hydration_pct = (hydration_w / flour_w * 100.0) if (flour_w and flour_w > 0) else np.nan
        st.metric("含水率（概算）", f"{hydration_pct:.1f}%" if pd.notna(hydration_pct) else "-")

    st.divider()
    st.subheader("スケーリング")
    c1, c2, c3 = st.columns(3)
    with c1:
        pieces = st.number_input("作りたい個数", min_value=1, value=1, step=1)
    with c2:
        each_weight = st.number_input("1個あたりの目標重量[g]（任意）", min_value=0.0, value=0.0, step=10.0)
    with c3:
        total_target = st.number_input("合計の目標重量[g]（任意）", min_value=0.0, value=0.0, step=10.0)

    if st.button("スケーリングを適用", use_container_width=True):
        if total_target > 0:
            new_total = total_target
        elif each_weight > 0:
            new_total = each_weight * pieces
        else:
            new_total = total_w

        scale = new_total / total_w if total_w > 0 else 1.0
        scaled_df = out_df.copy()
        scaled_df["重さ(g)"] = (scaled_df["重さ(g)"] * scale).round(1)
        st.markdown(" #### スケーリング結果")
        st.dataframe(scaled_df, use_container_width=True)
        st.info(f"総重量を {total_w:.1f} g → {new_total:.1f} g にスケール（倍率 x{scale:.3f}）。")

        csv = scaled_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSVをダウンロード", data=csv, file_name="scaled_recipe.csv", mime="text/csv")
        json_bytes = scaled_df.to_json(orient="records", force_ascii=False).encode("utf-8")
        st.download_button("JSONをダウンロード", data=json_bytes, file_name="scaled_recipe.json", mime="application/json")
    else:
        csv = out_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("結果CSVをダウンロード", data=csv, file_name="result_recipe.csv", mime="text/csv")
        json_bytes = out_df.to_json(orient="records", force_ascii=False).encode("utf-8")
        st.download_button("結果JSONをダウンロード", data=json_bytes, file_name="result_recipe.json", mime="application/json")

st.divider()
with st.expander("💡使い方のヒント"):
    st.markdown(
        """
- **粉扱いの行**（強力粉・全粒粉など）はサイドバーの語句で自動判定します。必要に応じて語を追加してください。
- **重さ→%**：各行の重さを入れれば粉合計を100%として%が出ます。
- **%→重さ**：粉重量または総生地重量を指定すれば自動でグラム計算します（未指定でも仮の粉300gを使います）。
- **含水率**は、水・牛乳・卵などを簡易に水分とみなして概算します。
- **スケーリング**：合計目標（もしくは1個あたり×個数）を入れて実行します。
"""
    )

st.caption("© 2025 Baker's % Helper — Streamlitで動作します。")
