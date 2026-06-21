# OpenTSC v1.0 — Soul/Shell Architecture

OpenTSC 是一个面向 Claude Code / Agent 的项目级技能包。v1.0 实现了**魂壳分离架构**：把人对人际世界的隐性判断变成显式的、结构化的、可查询的、可校准的、会自我进化的情报系统。

## 核心升级 (v0.4 → v1.0)

| 维度 | v0.4 (原料系统) | v1.0 (情报系统) |
|---|---|---|
| 事件 | 嵌入实体 timeline | **独立节点图谱** (soul/events/)，多实体链接，因果边 |
| 属性 | 手填 TODO | **K7 判断引擎自动推导**，三层属性 (base/skills/states) |
| 评价标准 | 存在模型权重里 | **判断法典** (judgment_codex)，显式可审计 |
| 预测 | 有但不校准 | **校准闭环**：预测→跟踪→命中率→法典迭代 |
| 架构 | 扁平文件夹 | **魂壳分离**：soul/ 可导出复活，shell/ 可替换 |
| 人物模型 | 扁平 skills 数组 | **AttributeClaim**：{value, confidence, provenance, decay} |
| 自创生 | 无 | **K8 引擎**：检测缺口→生成 Agent→校验→审批 |
| 职业 | 无 | **11 个 VSM 职业**，可分配给人或 Agent |

## 目录结构

```text
.claude/skills/opentsc/
├── SKILL.md                    # Skill 入口 (v1.0)
├── README.md
├── references/
│   ├── philosophy.md           # 十二法则
│   ├── data-contract.md        # 魂壳世界数据契约
│   ├── kernel.md               # K1-K8 内核
│   └── plugins.md              # 模块族契约
├── workflows/
│   └── core-workflows.md
├── templates/
│   ├── person_v1.md            # v1.0 三层属性人物模板
│   ├── event.md                # 事件节点模板
│   ├── profession.md           # 职业契约模板
│   ├── genesis_seed.md         # 创世层种子
│   ├── judgment_codex_seed.md  # 判断法典种子
│   ├── rule_codex_seed.md      # 规则法典种子
│   └── ...                     # 旧版模板保留
├── scripts/
│   ├── opentsc.py              # CLI 入口 (v1.0 + 旧版兼容)
│   └── opentsc_core/
│       ├── soul.py             # 魂管理：创世、法典、导出/导入
│       ├── events.py           # K3 事件图谱引擎
│       ├── judgment.py         # K7 判断引擎 (核心创新)
│       ├── world.py            # 世界模型：玩家/NPC/组织/任务
│       ├── identity.py         # K1 身份服务
│       ├── professions.py      # 11 个 VSM 职业
│       ├── genesis_engine.py   # K8 自创生引擎
│       ├── schema_mgr.py       # K5 字段本体
│       ├── migrate.py          # v0.4 → v1.0 迁移
│       └── ...                 # 旧版模块增强保留
├── examples/
│   └── contacts.csv
└── tests/
    └── smoke.py
```

## Vault 结构 (v1.0)

```text
opentsc/
├── soul/                        # 魂：可导出、可复活
│   ├── _genesis.md              # 创世层 (write-once)
│   ├── _rule_codex.md           # 规则法典
│   ├── _judgment_codex.md       # 判断法典
│   ├── _schema.md               # 字段本体
│   ├── events/YYYY-MM/evt_*.md  # 事件图谱
│   └── calibration/             # 校准记忆
├── shell/                       # 壳：可替换
│   ├── modules/_registry.md     # 模块注册表
│   ├── professions/*.md         # 11 个职业定义
│   └── genesis_engine/          # 自创生模板
├── world/                       # 世界模型
│   ├── players/p_*/             # 玩家
│   ├── npcs/humans/p_*/         # 人类 NPC (不可控)
│   ├── npcs/agents/a_*/         # Agent NPC (可控)
│   ├── orgs/o_*/                # 组织
│   └── operations/op_*/         # 任务
├── raw/, inbox/, knowledge/, actions/, relations/, reports/, archive/, ledger/
```

## CLI 命令

### 新增命令组 (v1.0)

```bash
# 魂管理
opentsc soul-init                                  # 初始化魂
opentsc soul-export <目标路径>                      # 导出魂
opentsc soul-import <来源路径>                      # 导入魂（复活）
opentsc soul-genesis                               # 查看创世层
opentsc soul-codex judgment|rule                   # 查看法典
opentsc soul-amend judgment|rule <section> <change> --reason <reason>

# 世界模型
opentsc world-new-player <name>                    # 创建玩家
opentsc world-new-npc <name> [--type human|agent]  # 创建 NPC
opentsc world-new-org <name>                       # 创建组织
opentsc world-new-operation <title>                # 创建任务

# 事件图谱
opentsc event-add <admiralty> <content> <source> --link <entity>...   # 添加事件
opentsc event-link <event_id> <entity>...          # 链接事件到实体
opentsc event-cause <from> <to>                    # 因果边
opentsc event-timeline [--entity <id>]             # 时间线查询
opentsc event-neighborhood <entity_id>             # 邻域图谱

# 判断引擎 (K7)
opentsc judgment-attribute <entity_id> <dimension> # 查看属性
opentsc judgment-compare <id_a> <id_b> <dimension> # 直接比较
opentsc judgment-explain <entity_id> <dimension>   # 解释属性来源
opentsc judgment-decay                             # 衰减过时属性
opentsc judgment-clean-states                      # 清理过期 buff/debuff

# 职业
opentsc profession-list                            # 列出所有职业
opentsc profession-gaps                            # 检测职业缺口
opentsc profession-assign <entity_id> <profession> # 分配职业

# 自创生
opentsc genesis-detect-gaps                        # 检测能力缺口
opentsc genesis-spawn <profession>                 # 生成 Agent 草案
opentsc genesis-register <draft_id>                # 注册（需玩家批准）

# 迁移
opentsc migrate                                    # v0.4 → v1.0 迁移
```

### 旧版命令 (完全兼容)

所有 v0.4 命令保留：`new-person`, `add-event`, `query`, `who-can`, `link`, `tag`, `action-new`, `calibrate`, `brief` 等。v1 vault 下自动路由到新架构。

## 关键概念

### AttributeClaim — 每个属性值都是带证据的概率声明

```yaml
reliability:
  value: 0.72           # 当前估计
  confidence: 0.6       # 这个估计有多确定
  provenance: [evt_0a1] # 凭哪些事件
  reviewed: 2026-06-01  # 上次更新
  decay: 0.03           # 没有新证据每月衰减
```

### 三层属性

- **base** (天赋，慢变)：执行力上限、学习速度、抗压能力、可靠性基线、自主性
- **skills** (技能树，事件驱动升级)：谈判 Lv.3、客户心理 Lv.5
- **states** (临时 buff/debuff，带倒计时)：已读不回·可靠性存疑 (7天后清除)

### 判断引擎 (K7)

添加事件时自动触发：
1. 读取 judgment_codex 中的评分维度
2. 匹配事件内容与触发词
3. 计算属性变更（正面 +0.05, 负面 -0.05）
4. 检查 buff/debuff 规则
5. 更新实体文件，留推理痕迹

**直接比较**：`judgment-compare p_carol p_dave negotiation` → 不重读历史，直接从属性值回答

## 快速开始

```bash
# 1. 初始化 v1.0 vault
python scripts/opentsc.py init

# 2. 创建人物
python scripts/opentsc.py world-new-npc "Carol" --id p_carol --tag core_team

# 3. 添加事件（自动触发判断引擎）
python scripts/opentsc.py event-add B2 "Carol 按时完成报价文档交付" "会议纪要" --link p_carol

# 4. 查看属性
python scripts/opentsc.py judgment-attribute p_carol execution_ceiling

# 5. 比较两人
python scripts/opentsc.py judgment-compare p_carol p_dave reliability

# 6. 查看简报
python scripts/opentsc.py brief
```

## 迁移指南

已有 v0.4 vault 用户：

```bash
python scripts/opentsc.py --root your_vault migrate
```

迁移会：
- 创建 soul/shell/world/ 目录
- 移动 people/ → world/npcs/humans/
- 提取内嵌事件 → soul/events/ 独立节点
- 生成 judgment_codex 种子
- 初始化 11 个 VSM 职业
- 保留所有原始数据

所有旧版命令继续工作，v1 vault 下自动路由到新架构。
