---
type: rule_codex
version: 1
last_amended: TODO(YYYY-MM-DD)
---

# Rule Codex — 规则法典

## 创世层（不可变，继承 _genesis.md）

见 soul/_genesis.md。此层字段不可在本文档修改。

## 宪法层（改需高门槛）

amendment_threshold: player_unanimous
sunset: never

- 所有实体使用稳定 ID，不用名字锚定路径
- 事件流 append-only，修正追加新事件，删除软删除
- 事件必须带 Admiralty 评级与来源
- 建议/预测必须带到期日与推理链
- 属性只能由判断引擎从事件推导，禁止直接写入
- 评价维度运行时从判断法典读取，不得硬编码
- 自创生产出的模块必须过校验门 + 玩家批准
- 任务完成/放弃仅玩家可宣告

## 操作层（改需简单多数，每条带 12 月自动日落）

- TODO(user): 具体操作规则
