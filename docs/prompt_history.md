# Prompt 演进史(情感判定规则部分)

三个版本只有**情感判定规则**一节发生变化,其余部分(主题标签枚举、本地化问题、
摘要要求、JSON 格式约束)保持不变。准确率均为同一批 50 条人工盲标样本上的结果。

---

## v1 — 零样本(准确率 90%)

```
- "sentiment": 情感分类,只能是 "positive" / "negative" / "neutral" / "mixed" 之一。
  注意:星级仅供参考,以评论文字实际表达为准;讽刺、反话要识别出来。
  "mixed" 指同时明确表达了正面和负面(如"画面很棒但总是闪退")。
```

仅一句任务描述。讽刺识别表现已良好(繁中 1 星"你蠻幽默的"正确判 negative),
主要错误:①"整体好评+具体抱怨"误判 positive;②温吞/建议式评论误判出情绪。

## v2 — 规则初版 + few-shot(准确率 88% ⬇)

```
  判定规则(按优先级):
  1. 星级仅供参考,以评论文字实际表达为准;讽刺、反话要识别出来。
  2. 只要评论点出了任何一个具体、明确的问题或缺点(操作难用、强制绑定账号、
     bug、卡顿等),即使整体态度是满意的,也判 "mixed",不判 "positive"。
     只有泛泛让步、没有具体问题的(如"虽然不完美但很好玩")才判 "positive"。
  3. 平铺直叙提建议、和其他游戏/前作做对比、"还好/一般/凑合"式温吞表态,
     没有明显情绪倾向的,判 "neutral",不要拔高成 mixed 或 positive/negative。
  4. 纯表情或无实质文字的评论,按星级折算:4~5星 -> "positive",
     3星 -> "neutral",1~2星 -> "negative"。

  示例:
  - "graphics are great but the shooting controls are frustrating"(5星) -> "mixed"
  - "fun game, just wish there was more content"(5星) -> "mixed"     ← 这条示例是错误示范
  - "希望增加跳过教程的选项,另外卡面可以参考前作的设计"(4星) -> "neutral"
  - "还行吧,免费游戏就这个水平"(3星) -> "neutral"
  - "👌"(5星) -> "positive"
```

修复了 v1 的 4 条错误,但**新引入 5 条**:规则 2 把"许愿新增内容"也当成了问题
抱怨(连 few-shot 示例本身都写错了口径);规则 3 把"good"这类明确褒义短评
吞进了 neutral。净效果 -2 条。

## v3 — 边界细化(准确率 92% ✅ 最终版)

```
  判定规则(按优先级):
  1. 星级仅供参考,以评论文字实际表达为准;讽刺、反话要识别出来。
  2. "mixed" = 明确的正面评价 + 抱怨**现存的具体问题**(操作难用、强制绑定
     账号、bug、延迟卡顿等)。注意区分:"希望新增/加入某功能某内容"属于许愿
     和建议,不是问题抱怨——整体好评 + 许愿 -> "positive"。
  3. 通篇以抱怨为主、正面内容只是轻描淡写地顺带一提 -> "negative",不是 "mixed"。
  4. "neutral" = 有实质内容但通篇平铺直叙(纯建议、和前作对比、评测式陈述),
     无明显情绪词。注意:"good"、"不错"这类明确褒义的短评是 "positive"。
  5. 文字信息量过少、无法从文字判断情绪的(纯表情、"okay"式模糊短语),
     按星级折算:4~5星 -> "positive",3星 -> "neutral",1~2星 -> "negative"。

  示例:
  - "graphics are great but the input lag online is frustrating"(5星) -> "mixed"(规则2:现存问题)
  - "great game hope they add more legends to collect"(5星) -> "positive"(规则2:许愿不是抱怨)
  - "servers are trash, constant lag. graphics are fine i guess"(2星) -> "negative"(规则3:抱怨为主)
  - "希望增加跳过教程的选项,另外卡面可以参考前作的设计"(4星) -> "neutral"(规则4:纯建议,无情绪)
  - "good"(3星) -> "positive"(规则4注意项:明确褒义短评)
  - "okay"(4星) -> "positive";"okay"(3星) -> "neutral"(规则5:信息量过少按星级)
  - "👌"(5星) -> "positive"(规则5:纯表情按星级)
```

相对 v2 的关键变化:**"现存问题"与"许愿建议"分家**(规则 2)、新增"抱怨为主
判 negative"(规则 3)、褒义短评例外(规则 4)、"信息量不足按星级折算"从纯表情
推广到模糊短语(规则 5)。相对 v1 修复 2 条、新引入 1 条,净 +2。

---

所有版本的错误分析、方法论决策(仿写 few-shot 防泄漏、止步 v3 防过拟合)见
[calibration.md](calibration.md);逐条对比数据见 `data/calibration_results.csv`。
