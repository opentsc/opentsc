# 更新日志 / Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
配套白皮书（魂）的版本见 [opentsc/tsc](https://github.com/opentsc/tsc)。

---

## [2.1.0] — 2026-06-21

> **主题：LLM 情绪后端 + token 节流，外加修正默认情绪的反向误判。**

### 新增 Added
- **`llm` 情绪后端**：用大模型打分，**自带三重 token 节流**——① 按文本哈希**持久缓存**（cron 重跑已见文本零成本）；② **批量**一次调用打一批；③ 命令式接口，provider 无关。示例脚本 `scripts/emotion_llm_example.py`（OpenAI 兼容）。
- **`hybrid` 情绪后端**：词典先打，**只有不确定的少数句子才升级给 LLM**——明显的情绪免费搞定，大模型只花在刀刃上。`emotion_escalate_threshold` 可调。
- 配置项 `emotion_escalate_threshold`、`emotion_cache`。

### 修复 Fixed
- **默认情绪反向误判**：snownlp 对"拖延/烦躁/积极/主动"等短业务文本经常判反，导致 `index-mood`"谁情绪不好"排名颠倒。改为**精校领域词典优先**（零依赖、对业务/关系文本已校准），snownlp 降为无领域词时的兜底。受影响的 mood 聚合现已正确（拖延=负、积极=正）。

### 测试
- 新增 9 项：领域词典正确性、LLM 批量+缓存、hybrid 仅升级模糊句。共 27 项。

---

## [2.0.0] — 2026-06-21

> **主题：可插拔记忆引擎 + 确定性优先（CLI-first）。** 把"LLM 每次重读 markdown 重算"换成"确定性 Python 管线 + zvec 索引，LLM 只做判断"。

### 新增 Added
- **可插拔记忆索引（zvec）** `index.py`：markdown 仍是真源，zvec 是可重建的派生索引（`soul/.index/`，已 gitignore）。语义搜索、混合检索、身份解析。
- **可插拔向量后端** `embedding.py`：`lite`（零依赖哈希向量，默认）/ `local`（本地 BGE/M3E 模型）/ `api`。
- **可插拔情绪后端** `emotion.py`：`lexicon`（snownlp，默认）/ `model`（本地分类模型）/ `llm`（外部命令）。情绪在建索引时预计算，写入事件、聚合成实体 mood。
- **中文文本处理** `text.py`：jieba 分词 + 关键词，jieba 缺失时降级到正则。
- **中央配置** `config.py`：`soul/_config.yaml` + 环境变量选择后端。
- **新 CLI 命令**：`index-build` `index-sync` `index-search` `identity-resolve` `index-mood` `index-stats` `emotion-score` `text-segment` `actions-stale` `config-show`。
- **数据源扩展契约** `references/extending-with-skills.md`：微信/邮件/逐字稿等采集器是**用户自建技能**，通过 CLI 接入，不进核心。
- `requirements.txt`（可选依赖）、`templates/_config.yaml`、`tests/test_v2.py`（18 项，CI 运行）。

### 变更 Changed
- **SKILL.md → v2.0**：新增「记忆与确定性」段、**CLI-first 强制约束**（禁止手扫/手写 vault）、v2 模块图与命令清单。
- **身份解析**取代"LLM 猜名字"：先 `identity-resolve` 找最近实体，再决定新建/合并——根治 hash-ID 泛滥与"马克思 vs 马斯克"漂移。
- 实体的可检索表示 = 名字 + 其所有事件叙述聚合（实体即其事件之和）。

### 修复 Fixed
- 僵尸行动堆积 → `actions-stale`（按陈旧度/逾期确定性筛出）。
- YAML frontmatter 漂移 → `parse/write_frontmatter` round-trip 测试锁定。
- cron 每次全扫无记忆 → 改查 zvec 增量索引。

### 设计原则 Design
- **核心零依赖也能跑**：`lite` 向量 + 内置情绪词典 + 正则分词永远可用；jieba/snownlp/zvec/本地模型全部 opt-in。
- **魂可移植不变**（法则二）：索引是派生物，可随时从 markdown 重建。

### 升级须知
见 [MIGRATION.md](MIGRATION.md)。v1.0 vault **无需改动数据**即可升级；新能力按需开启。

---

## [1.0.0] — 2026-06

首个公开版本。魂壳分离架构：事件图谱（K3）、判断引擎（K7）、自创生（K8）、三层属性、校准预测、11 个 VSM 职业、82 个 CLI 命令。
