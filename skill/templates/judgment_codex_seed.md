---
type: judgment_codex
version: 1
last_amended: TODO(YYYY-MM-DD)
---

# Judgment Codex — 判断法典

## 评分维度 (scoring_dimensions)

### execution_ceiling — 执行力上限
- triggers: ["完成", "交付", "执行", "落地", "推进"]
- positive: ["按时完成", "超额完成", "主动推进", "独立执行"]
- negative: ["拖延", "未完成", "需要反复催促", "半途而废"]
- default_decay: 0.02
- layer: base

### learning_speed — 学习速度
- triggers: ["学会", "掌握", "理解", "上手", "适应"]
- positive: ["快速掌握", "举一反三", "自主学习"]
- negative: ["反复教不会", "无法迁移", "依赖手把手"]
- default_decay: 0.02
- layer: base

### resilience — 抗压能力
- triggers: ["压力", "困难", "挫折", "变化", "冲突"]
- positive: ["扛住压力", "逆境翻盘", "情绪稳定", "坚持到底"]
- negative: ["崩溃", "逃避", "情绪失控", "放弃"]
- default_decay: 0.02
- layer: base

### reliability — 可靠性基线
- triggers: ["承诺", "截止", "交付", "回复", "到场"]
- positive: ["守约", "准时", "说到做到", "主动反馈"]
- negative: ["爽约", "迟到", "已读不回", "失联", "食言"]
- default_decay: 0.02
- layer: base

### autonomy — 自主性
- triggers: ["主动", "自发", "独立", "不需要催"]
- positive: ["主动发现问题", "自主决策", "不等指令"]
- negative: ["等指令", "被动", "什么都问", "不敢决定"]
- default_decay: 0.02
- layer: base

## 技能树定义 (skill_tree)

### negotiation — 谈判
- levels:
  1: "能参与简单谈判"
  2: "能独立处理常规议价"
  3: "能设计谈判策略"
  4: "能处理复杂多方谈判"
  5: "能在逆境中翻盘"
- prereqs: []
- upgrade_triggers: ["成功议价", "达成协议", "扭转谈判局面"]
- layer: skill

### client_psych — 客户心理分析
- levels:
  1: "能识别基本情绪"
  2: "能判断客户意图"
  3: "能预判客户反应"
  4: "能设计情绪引导路径"
  5: "能构建长期心理模型"
- prereqs: []
- upgrade_triggers: ["成功预判客户反应", "设计有效的情绪策略"]
- layer: skill

### quote_rewrite — 报价重构
- levels:
  1: "能调整报价"
  2: "能基于竞品调价"
  3: "能设计报价策略"
  4: "能重构报价体系"
  5: "能创造新定价模式"
- prereqs: [{skill: client_psych, min_level: 2}]
- upgrade_triggers: ["设计新报价方案", "报价策略被采纳"]
- layer: skill

### industry_insight — 行业洞察
- levels:
  1: "了解行业基本面"
  2: "能分析竞品"
  3: "能判断行业趋势"
  4: "能预测市场变化"
  5: "能发现行业盲区"
- prereqs: []
- upgrade_triggers: ["产出有价值的行业分析", "预判被市场验证"]
- layer: skill

## Buff/Debuff 规则 (state_rules)

### 已读不回·可靠性存疑
- pattern: "已读不回"
- kind: debuff
- tag: "已读不回·可靠性存疑"
- duration_days: 7
- on_repeat: solidify
- affects: [reliability]
- delta: -0.15

### 关键时刻掉链子
- pattern: "关键时刻.*(?:掉链子|消失|失联|不回)"
- kind: debuff
- tag: "关键时刻不可靠"
- duration_days: 30
- on_repeat: solidify
- affects: [reliability, resilience]
- delta: -0.2

### 超预期交付
- pattern: "超预期|超额完成|提前完成"
- kind: buff
- tag: "超预期交付"
- duration_days: 14
- on_repeat: extend
- affects: [execution_ceiling, reliability]
- delta: 0.1

## 可调动度公式 (leverage)

leverage = value × accessibility × relationship_health − mobilization_cost

- value: 该人在目标任务上的能力匹配度（技能等级 × 基础属性）
- accessibility: 可达性（有联系方式? 最近联系过? 关系活跃?）
- relationship_health: 关系健康度（信任 × 最近互动质量）
- mobilization_cost: 调动成本（需要什么回报? 欠多大人情?）

## 迭代记录

- TODO(YYYY-MM): 初始版本，待实战校准
