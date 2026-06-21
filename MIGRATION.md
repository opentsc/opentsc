# 迁移说明：v1.0 → v2.0

**好消息：你的 vault 数据一个字都不用改。** v2.0 完全向后兼容 v1.0 的 markdown 布局；新能力是叠加上去的，按需开启。下面三步走完即可用上记忆引擎。

---

## 0. 零改动也能跑

如果你只升级代码、不装任何可选依赖，v2.0 一切照旧：

- 所有 v1.0 命令照常工作；
- `text-segment` 用正则分词、`emotion-score` 用内置词典、`config-show` 用默认配置；
- 只有 `index-*` 命令会提示需要 `zvec`。

**核心零依赖也能跑**是设计底线，不是降级。

---

## 1. （可选）安装你要的后端依赖

核心不强制任何第三方库。只装你在 `_config.yaml` 里选的那个后端：

```bash
# 推荐起步组合：jieba 分词 + snownlp 情绪 + zvec 索引（均轻量）
pip install jieba snownlp zvec        # zvec 需 Python 3.10–3.14

# 仅当你把 embedding_backend 设为 local 时：
# pip install sentence-transformers    # 例如 BAAI/bge-small-zh-v1.5
# 仅当你把 emotion_backend 设为 model 时：
# pip install transformers
```

> 在受 PEP 668 限制的系统上用虚拟环境：`python -m venv .venv && . .venv/bin/activate`。
> cron 运行时记得用同一个解释器/venv。

## 2. （可选）写配置选后端

复制模板到你的 vault：

```bash
cp .claude/skills/opentsc/templates/_config.yaml <你的vault>/soul/_config.yaml
```

关键两行（省略即用默认 `lite` / `lexicon`）：

```yaml
embedding_backend: lite        # lite(零依赖) | local(本地模型) | api
emotion_backend: lexicon       # lexicon(snownlp) | model(本地模型) | llm
```

环境变量可临时覆盖：`OPENTSC_EMBEDDING_BACKEND=local`。

> **情绪准确度提示**：默认 `lexicon`(snownlp) 训练自商品评论，对"按时交付质量很高"这类业务文本可能误判。要更准就设 `emotion_backend: model`。

## 3. 首次建索引

```bash
python .claude/skills/opentsc/scripts/opentsc.py --root <你的vault> index-build
```

之后增量同步（建议放进每小时 cron，取代"全库重扫"）：

```bash
python .../opentsc.py --root <你的vault> index-sync
```

索引落在 `<vault>/soul/.index/`，**派生、可删、可重建**——删了再 `index-build` 即可，不影响 markdown 真源。

---

## 切换后端后要重建

把 `embedding_backend` 从 `lite` 换成 `local`（或改了维度）后，向量空间变了，需要重建一次：

```bash
python .../opentsc.py --root <你的vault> index-build
```

`index-sync` 会自动检测后端/维度漂移并触发重建，所以放进 cron 也安全。

---

## 把"全库重扫"换成命令（省 token 的关键）

| 旧做法（LLM 裸扫） | v2.0 命令 |
|---|---|
| 读所有档案找某人 | `identity-resolve "名字"` |
| 读所有事件找相似情况 | `index-search "描述" --kind event` |
| 读所有消息判断谁情绪差 | `index-mood` |
| 扫 actions/active 找过期 | `actions-stale --days 30` |
| 让 LLM 数行动/算状态 | `actions` / `derive-view` |

详见 SKILL.md 的「CLI-first 强制约束」。
