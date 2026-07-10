# 游戏玩家评论智能分析工具 — 开发方案

> 目标:做一个能写进简历、对齐游戏行业 AI 分析岗 JD 的作品集项目。
> 核心卖点:多语言评论抓取 → LLM 情感/主题/本地化分析 → 可视化面板 → **人工校准实验(准确率 v1→v2)**。

## 1. 项目目标

抓取 Google Play 上 **NBA 2K26 MyTEAM Mobile**(包名 `com.t2ksports.myteam2k26v2`)
的多语言玩家评论(英/西/葡/法/繁中),用 LLM 逐条分析:

- **情感分类**(positive / negative / neutral / mixed)
- **主题标签**(抽卡付费、剧情、角色、优化性能、活动、平衡性、本地化、客服…)
- **本地化问题识别**(翻译生硬、措辞不当、文本缺失)——对齐"国际化"业务场景
- 一句话摘要

结果存 CSV,用 Streamlit 做交互式分析面板,最后做**人工标注校准实验**证明可信度。

## 2. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.14(已装) | |
| 评论抓取 | google-play-scraper | 免账号、免费 |
| 数据处理 | pandas | |
| LLM | DeepSeek API(openai 库兼容接口) | 便宜,几块钱够整个项目;可随时换 Claude/OpenAI |
| 重试容错 | tenacity | API 调用失败自动重试 |
| 前端面板 | Streamlit + plotly | 纯 Python 写网页 |
| 密钥管理 | python-dotenv(.env) | 不进 git |

## 3. 项目结构

```
game-review-analyzer/
├── .env               # DEEPSEEK_API_KEY(不进 git)
├── .env.example       # 模板(进 git)
├── requirements.txt
├── data/              # 原始及分析后 CSV(不进 git)
├── src/
│   ├── scraper.py     # 抓取多语言评论 → data/reviews_raw.csv
│   ├── prompts.py     # 所有 Prompt 集中管理(便于迭代 = prompt 工程)
│   └── analyzer.py    # 逐条 LLM 分析,断点续跑 → data/reviews_analyzed.csv
├── app.py             # Streamlit 面板
└── docs/
    └── calibration.md # 校准实验记录(v1/v2 准确率)
```


## 4. 里程碑

### M0 环境(半小时内)
- venv + pip 安装依赖;你注册 DeepSeek 填 .env
- 验收:`python test_api.py` 能打印出一句 LLM 回复

### M1 数据抓取
- scraper.py 抓 5 个语言区:en-US(~300)/ es-ES(~300)/ pt-BR(~100)/
  fr-FR(~150)/ zh-TW(~120)——日/韩区该游戏评论过少(6 条/0 条),已实测放弃
- 验收:`data/reviews_raw.csv` 有 ~900 条去重评论
- ⚠️ 风险:国内网络访问 Google Play 可能需要代理;抓不到就先用 50 条小样本或换网络

### M2 LLM 分析管线(项目灵魂)
- prompts.py(结构化 JSON 输出)+ analyzer.py(temperature=0、断点续跑、每 20 条落盘)
- 验收:`data/reviews_analyzed.csv` 完整,字段齐全,失败率 < 5%
- 成本预估:900 条 × deepseek-chat ≈ 几块钱

### M3 Streamlit 面板
- 侧边栏筛选(语言/情感)+ 情感饼图 + 主题 Top10 条形图
- 本地化问题清单表 + 负面评论摘要表
- 加分项:「生成分析周报」按钮(把统计数字喂给 LLM 出一段运营视角中文总结)
- 验收:`streamlit run app.py` 面板可交互,截图放 README

### M4 校准实验(面试最值钱的部分)
1. 随机抽 50 条,你人工标注情感 → 对比 LLM 结果 = **v1 准确率**
2. 把典型错误(讽刺、黑话如"抽卡保底")做成 few-shot 加进 Prompt
3. 重跑同 50 条 = **v2 准确率**,两轮数字写进 docs/calibration.md 和 README
- 产出话术:"通过人工标注校准与 Prompt 迭代,情感分类准确率从 X% 提升至 Y%"


## 5. 风险与注意事项

- **网络**:google-play-scraper 需要能访问 Google Play,国内可能要代理
- **密钥安全**:.env 已 gitignore;绝不提交(校园导航项目里踩过一次坑)
- **Python 3.14 兼容性**:个别库若未适配,降级到 3.12 即可,结构不变
- **JSON 解析失败**:analyzer 里已设计容错(剥 markdown 代码块 + tenacity 重试)


