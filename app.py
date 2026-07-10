"""NBA 2K26 MyTEAM Mobile 多语言评论分析面板 (Streamlit)

运行: streamlit run app.py
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from prompts import REPORT_SYSTEM_PROMPT, build_report_prompt  # noqa: E402

DATA_PATH = ROOT / "data" / "reviews_analyzed.csv"

# ---------- 视觉常量(经过 CVD 校验的参考调色板) ----------
INK = "#0b0b0b"        # 主文字
INK_2 = "#52514e"      # 次级文字
MUTED = "#898781"      # 坐标轴/刻度
GRID = "#e1e0d9"       # 网格线
SURFACE = "#ffffff"    # 图表底(留给堆叠段之间的分隔缝)
SEQ_BLUE = "#2a78d6"   # 单色系(数量对比用)

# 情感 = 极性数据 -> 发散配色:红臂(负面/mixed 浅红) | 中性灰 | 蓝臂(正面)
SENT_ORDER = ["negative", "mixed", "neutral", "positive"]
SENT_COLORS = {
    "negative": "#e34948",
    "mixed": "#f2b8b7",
    "neutral": "#c3c2b7",
    "positive": "#2a78d6",
}
SENT_LABELS = {"negative": "负面", "mixed": "褒贬皆有", "neutral": "中性", "positive": "正面"}

LANG_LABELS = {"en": "英语", "es": "西班牙语", "pt": "葡语(巴西)", "fr": "法语", "zh-TW": "繁中(台湾)"}
TOPIC_LABELS = {
    "monetization": "抽卡/付费",
    "gameplay": "玩法/游戏性",
    "controls": "操作手感",
    "performance": "性能/帧率",
    "network": "联网/延迟",
    "account_login": "登录/账号",
    "ads": "广告",
    "content_updates": "内容/活动",
    "balance": "平衡性/匹配",
    "localization": "本地化/翻译",
    "customer_service": "客服",
    "other": "其他",
}

st.set_page_config(page_title="NBA 2K26 评论分析", page_icon="🏀", layout="wide")


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df[df["sentiment"].isin(SENT_ORDER)].copy()
    df["at"] = pd.to_datetime(df["at"])
    return df


def axis_style(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK_2, size=13),
        margin=dict(l=8, r=8, t=8, b=8),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=MUTED, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK_2))
    return fig


if not DATA_PATH.exists():
    st.warning("尚未生成分析结果。先运行: python src/analyzer.py")
    st.stop()

df = load_data()

# ---------- 侧边栏筛选 ----------
st.sidebar.header("筛选")
sel_langs = st.sidebar.multiselect(
    "语言", options=list(LANG_LABELS), default=list(LANG_LABELS),
    format_func=lambda x: LANG_LABELS.get(x, x),
)
sel_sents = st.sidebar.multiselect(
    "情感", options=SENT_ORDER, default=SENT_ORDER,
    format_func=lambda x: SENT_LABELS[x],
)
f = df[df["lang"].isin(sel_langs) & df["sentiment"].isin(sel_sents)]

st.title("🏀 NBA 2K26 MyTEAM Mobile — 玩家评论分析")
st.caption(
    f"Google Play 多语言评论 | 数据范围 {df['at'].min():%Y-%m-%d} ~ {df['at'].max():%Y-%m-%d}"
    f" | 共 {len(df)} 条(当前筛选 {len(f)} 条)"
)

# ---------- KPI 行 ----------
neg_share = (f["sentiment"] == "negative").mean() if len(f) else 0
k1, k2, k3, k4 = st.columns(4)
k1.metric("评论数", f"{len(f):,}")
k2.metric("平均星级", f"{f['score'].mean():.2f}" if len(f) else "—")
k3.metric("负面占比", f"{neg_share:.1%}")
k4.metric("本地化问题", int(f["localization_issue"].sum()))

st.divider()
col_left, col_right = st.columns(2)

# ---------- 图 1:各语言情感构成(发散堆叠条,以中性为轴) ----------
with col_left:
    st.subheader("各语言情感构成")
    langs_in = [l for l in LANG_LABELS if l in f["lang"].unique()]
    fig = go.Figure()
    pct = {}
    for lang in langs_in:
        sub = f[f["lang"] == lang]
        pct[lang] = {s: (sub["sentiment"] == s).mean() * 100 for s in SENT_ORDER}
    # 负臂(negative, mixed)取负值画在左侧,中性+正面在右侧,0 线即轴心
    for s in ["mixed", "negative"]:  # 先画 mixed 使 negative 靠外
        xs = [-pct[l][s] for l in langs_in]
        fig.add_bar(
            y=[LANG_LABELS[l] for l in langs_in], x=xs, name=SENT_LABELS[s],
            orientation="h", marker=dict(color=SENT_COLORS[s], line=dict(color=SURFACE, width=2)),
            text=[f"{-v:.0f}%" if v <= -5 else "" for v in xs], textposition="inside",
            insidetextfont=dict(color=INK if s == "mixed" else "#ffffff"),
            customdata=[[-v] for v in xs],
            hovertemplate="%{y} · " + SENT_LABELS[s] + ": %{customdata[0]:.1f}%<extra></extra>",
        )
    for s in ["neutral", "positive"]:
        xs = [pct[l][s] for l in langs_in]
        fig.add_bar(
            y=[LANG_LABELS[l] for l in langs_in], x=xs, name=SENT_LABELS[s],
            orientation="h", marker=dict(color=SENT_COLORS[s], line=dict(color=SURFACE, width=2)),
            text=[f"{v:.0f}%" if v >= 5 else "" for v in xs], textposition="inside",
            insidetextfont=dict(color=INK if s == "neutral" else "#ffffff"),
            hovertemplate="%{y} · " + SENT_LABELS[s] + ": %{x:.1f}%<extra></extra>",
        )
    fig.update_layout(barmode="relative", height=320,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    axis_style(fig)
    fig.update_xaxes(ticksuffix="%", tickvals=[-100, -50, 0, 50, 100],
                     ticktext=["100%", "50%", "0", "50%", "100%"])
    st.plotly_chart(fig, use_container_width=True)

# ---------- 图 2:主题 Top10(单色系条形图) ----------
with col_right:
    st.subheader("评论主题 Top10")
    topics = (
        f["topics"].dropna().str.split("|").explode().map(TOPIC_LABELS)
        .value_counts().head(10).sort_values()
    )
    fig2 = go.Figure(
        go.Bar(
            x=topics.values, y=topics.index, orientation="h",
            marker=dict(color=SEQ_BLUE),
            text=topics.values, textposition="outside", textfont=dict(color=INK_2),
            hovertemplate="%{y}: %{x} 条<extra></extra>",
        )
    )
    fig2.update_layout(height=320, showlegend=False)
    axis_style(fig2)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------- 表 1:本地化问题清单 ----------
st.subheader("⚠️ 本地化问题清单")
loc = f[f["localization_issue"] == True][["lang", "score", "at", "content", "loc_detail"]]  # noqa: E712
if len(loc):
    loc = loc.assign(lang=loc["lang"].map(LANG_LABELS)).rename(
        columns={"lang": "语言", "score": "星级", "at": "时间", "content": "评论原文", "loc_detail": "问题描述"}
    )
    st.dataframe(loc, use_container_width=True, hide_index=True)
else:
    st.info("当前筛选范围内没有本地化问题相关评论。")

# ---------- 表 2:负面评论明细 ----------
st.subheader("负面评论明细(按点赞数排序)")
neg = f[f["sentiment"].isin(["negative", "mixed"])].sort_values("thumbsUp", ascending=False)
neg_view = neg[["lang", "score", "thumbsUp", "topics", "summary_zh", "content"]].head(50)
neg_view = neg_view.assign(
    lang=neg_view["lang"].map(LANG_LABELS),
    topics=neg_view["topics"].fillna("").apply(
        lambda t: "、".join(TOPIC_LABELS.get(x, x) for x in t.split("|") if x)
    ),
).rename(columns={
    "lang": "语言", "score": "星级", "thumbsUp": "点赞", "topics": "主题",
    "summary_zh": "中文摘要", "content": "评论原文",
})
st.dataframe(neg_view, use_container_width=True, hide_index=True)

st.divider()

# ---------- 校准实验 ----------
CALIB_PATH = ROOT / "data" / "calibration_results.csv"
if CALIB_PATH.exists():
    st.subheader("🎯 校准实验:LLM vs 人工标注(50 条盲标样本)")
    st.caption(
        "从英文/繁中评论中分层盲抽 50 条人工标注作黄金标准,对比三个 prompt 版本的情感分类准确率。"
        "v2 的下降来自规则矫枉过正,由此细化出 v3 的判定边界——完整方法论见 docs/calibration.md"
    )
    calib = pd.read_csv(CALIB_PATH, encoding="utf-8-sig")
    versions = {"v1 零样本": "v1", "v2 规则初版": "v2", "v3 边界细化(最终)": "v3"}
    accs = {name: (calib["人工情感标注"] == calib[col]).mean() * 100 for name, col in versions.items()}

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**各版本准确率**")
        figc = go.Figure(
            go.Bar(
                x=list(accs.keys()), y=list(accs.values()),
                marker=dict(color=SEQ_BLUE),
                text=[f"{v:.0f}%" for v in accs.values()],
                textposition="outside", textfont=dict(color=INK),
                hovertemplate="%{x}: %{y:.0f}%<extra></extra>",
            )
        )
        figc.update_layout(height=300, showlegend=False)
        axis_style(figc)
        figc.update_yaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(figc, use_container_width=True)

    with cc2:
        st.markdown("**v3 混淆矩阵(行=人工,列=LLM)**")
        order_present = [s for s in SENT_ORDER if s in set(calib["人工情感标注"]) | set(calib["v3"])]
        cm = pd.crosstab(calib["人工情感标注"], calib["v3"]).reindex(
            index=order_present, columns=order_present, fill_value=0
        )
        figm = go.Figure(
            go.Heatmap(
                z=cm.values,
                x=[SENT_LABELS[s] for s in cm.columns],
                y=[SENT_LABELS[s] for s in cm.index],
                colorscale=[[0, "#f6f9fe"], [1, "#1c5cab"]],
                texttemplate="%{z}", textfont=dict(color=INK_2),
                showscale=False,
                hovertemplate="人工 %{y} × LLM %{x}: %{z} 条<extra></extra>",
            )
        )
        figm.update_layout(height=300)
        axis_style(figm)
        figm.update_yaxes(autorange="reversed")
        st.plotly_chart(figm, use_container_width=True)

    with st.expander(f"查看 v3 剩余分歧({int((calib['人工情感标注'] != calib['v3']).sum())} 条)"):
        diff = calib[calib["人工情感标注"] != calib["v3"]][
            ["lang", "score", "content", "人工情感标注", "v1", "v2", "v3"]
        ].rename(columns={"lang": "语言", "score": "星级", "content": "评论原文"})
        st.dataframe(diff, use_container_width=True, hide_index=True)

st.divider()

# ---------- 生成分析周报 ----------
st.subheader("📋 生成分析周报")
if st.button("用 LLM 生成本期分析周报", type="primary"):
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(ROOT / ".env")
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

    topics_neg = (
        f[f["sentiment"].isin(["negative", "mixed"])]["topics"]
        .dropna().str.split("|").explode().value_counts().head(5)
    )
    stats = {
        "数据范围": f"{f['at'].min():%Y-%m-%d} ~ {f['at'].max():%Y-%m-%d}",
        "评论总数": len(f),
        "平均星级": round(float(f["score"].mean()), 2),
        "情感分布": {SENT_LABELS[s]: int((f["sentiment"] == s).sum()) for s in SENT_ORDER},
        "各语言负面率": {
            LANG_LABELS[l]: f"{(f[f['lang'] == l]['sentiment'] == 'negative').mean():.1%}"
            for l in f["lang"].unique()
        },
        "负面评论主题Top5": {TOPIC_LABELS.get(k, k): int(v) for k, v in topics_neg.items()},
        "本地化问题数": int(f["localization_issue"].sum()),
        "本地化问题示例": f[f["localization_issue"] == True]["loc_detail"].head(5).tolist(),  # noqa: E712
    }
    with st.spinner("生成中…"):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            temperature=0,
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": build_report_prompt(json.dumps(stats, ensure_ascii=False, indent=1))},
            ],
        )
    st.markdown(resp.choices[0].message.content)
