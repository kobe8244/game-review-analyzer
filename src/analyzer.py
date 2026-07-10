"""逐条 LLM 分析评论 -> data/reviews_analyzed.csv

- DeepSeek API(openai 兼容接口),temperature=0,JSON 模式
- 断点续跑:每 20 条落盘;重跑时自动跳过已分析的 reviewId
- 用法:
    python src/analyzer.py            # 全量
    python src/analyzer.py --limit 10 # 小样本试跑
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import PROMPT_VERSION, SYSTEM_PROMPT, TOPIC_TAGS, build_user_prompt

ROOT = Path(__file__).resolve().parent.parent
IN_PATH = ROOT / "data" / "reviews_raw.csv"
OUT_PATH = ROOT / "data" / "reviews_analyzed.csv"
CHECKPOINT_EVERY = 20

VALID_SENTIMENTS = {"positive", "negative", "neutral", "mixed"}

load_dotenv(ROOT / ".env")
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

total_in_tokens = 0
total_out_tokens = 0


def parse_json(text: str) -> dict:
    """剥掉可能的 markdown 代码块后解析 JSON。"""
    text = text.strip()
    if text.startswith("```"):
        text = text[text.find("{"): text.rfind("}") + 1]
    return json.loads(text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=20))
def analyze_one(content: str, lang: str, score: int) -> dict:
    global total_in_tokens, total_out_tokens
    resp = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(content, lang, score)},
        ],
    )
    total_in_tokens += resp.usage.prompt_tokens
    total_out_tokens += resp.usage.completion_tokens

    data = parse_json(resp.choices[0].message.content)

    # 字段校验与兜底
    sentiment = data.get("sentiment", "")
    if sentiment not in VALID_SENTIMENTS:
        raise ValueError(f"非法 sentiment: {sentiment!r}")
    topics = [t for t in data.get("topics", []) if t in TOPIC_TAGS] or ["other"]
    return {
        "sentiment": sentiment,
        "topics": "|".join(topics),
        "localization_issue": bool(data.get("localization_issue", False)),
        "loc_detail": str(data.get("loc_detail", "")),
        "summary_zh": str(data.get("summary_zh", "")),
        "prompt_version": PROMPT_VERSION,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="只分析前 N 条(试跑用)")
    args = ap.parse_args()

    df = pd.read_csv(IN_PATH)
    if args.limit:
        # 按语言分层取样(每语言取 limit/语言数 条),让试跑覆盖所有语言
        per = max(1, args.limit // df["lang"].nunique())
        df = df.groupby("lang", sort=False).head(per)

    # 断点续跑:加载已有结果,跳过已完成的
    done: dict[str, dict] = {}
    if OUT_PATH.exists():
        prev = pd.read_csv(OUT_PATH)
        done = {rec["reviewId"]: rec for rec in prev.to_dict("records")}
        print(f"检测到已有结果 {len(done)} 条,将跳过")

    results = list(done.values())
    todo = df[~df["reviewId"].isin(done.keys())]
    print(f"待分析: {len(todo)} 条\n")

    failed = 0
    for i, (_, row) in enumerate(todo.iterrows(), 1):
        try:
            analysis = analyze_one(row["content"], row["lang"], row["score"])
        except Exception as e:
            print(f"  [{i}] {row['reviewId'][:16]}... 失败: {type(e).__name__}")
            failed += 1
            analysis = {
                "sentiment": "error",
                "topics": "",
                "localization_issue": False,
                "loc_detail": "",
                "summary_zh": "",
                "prompt_version": PROMPT_VERSION,
            }
        results.append({**row.to_dict(), **analysis})

        if i % CHECKPOINT_EVERY == 0 or i == len(todo):
            pd.DataFrame(results).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
            print(f"[{i}/{len(todo)}] 已落盘 {len(results)} 条")

    est_cost = total_in_tokens / 1e6 * 2 + total_out_tokens / 1e6 * 8  # deepseek-chat 约 ¥2/¥8 每百万
    print(f"\n完成。失败 {failed} 条(失败率 {failed / max(len(todo), 1):.1%})")
    print(f"tokens: 输入 {total_in_tokens:,} / 输出 {total_out_tokens:,},本次成本约 ¥{est_cost:.2f}")
    print(f"输出 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
