"""抓取 NBA 2K26 MyTEAM Mobile 的多语言 Google Play 评论 -> data/reviews_raw.csv

语言组合为实测有足够评论量的 5 个语言区(日/韩区评论过少已放弃):
en-US / es-ES / pt-BR / fr-FR / zh-TW
"""
import sys
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews

sys.stdout.reconfigure(encoding="utf-8")

APP_ID = "com.t2ksports.myteam2k26v2"

# (语言, 国家区, 抓取上限) —— 上限按实测可用量设置,实际以抓到为准
TARGETS = [
    ("en", "us", 300),
    ("es", "es", 300),
    ("pt", "br", 200),
    ("fr", "fr", 200),
    ("zh-TW", "tw", 200),
]

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "reviews_raw.csv"


def fetch_language(lang: str, country: str, max_count: int) -> list[dict]:
    result, _ = reviews(
        APP_ID, lang=lang, country=country, sort=Sort.NEWEST, count=max_count
    )
    rows = []
    for r in result:
        content = (r.get("content") or "").strip()
        if not content:
            continue
        rows.append(
            {
                "reviewId": r["reviewId"],
                "lang": lang,
                "country": country,
                "score": r["score"],
                "at": r["at"],
                "content": content,
                "thumbsUp": r.get("thumbsUpCount", 0),
                "appVersion": r.get("appVersion") or "",
            }
        )
    return rows


def main() -> None:
    all_rows = []
    for lang, country, max_count in TARGETS:
        rows = fetch_language(lang, country, max_count)
        print(f"{lang}-{country}: {len(rows)} 条")
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.drop_duplicates(subset="reviewId")
    df = df.sort_values("at", ascending=False).reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig:让 Excel 直接打开不乱码(人工标注时要用)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"\n合计 {before} 条,去重后 {len(df)} 条 -> {OUT_PATH}")
    print("\n各语言分布:")
    print(df["lang"].value_counts().to_string())


if __name__ == "__main__":
    main()
