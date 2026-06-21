# OpenTSC v2.0 使用说明

面向"我装好了，怎么用"。命令统一前缀（把它设成别名最省事）：

```bash
alias tsc='python /path/to/.claude/skills/opentsc/scripts/opentsc.py --root /path/to/your-vault'
```

下文一律用 `tsc <command>`。

---

## 1. 初始化

```bash
tsc init                 # 建 soul/shell/world 目录结构（首次）
tsc config-show          # 看当前用的是哪套后端
```

## 2. 录入情报（始终经 CLI，绝不手写文件）

```bash
# 新建实体
tsc world-new-npc "Carol" --id p_carol --tag core_team

# 追加一条带证据的事件（Admiralty 评级 + 来源，缺一不可）
tsc event-add B2 "Carol 按时完成报价文档交付，质量很高" "会议纪要" --link p_carol

# 先草稿后入册：自动抽取落 inbox/，确认后才正式入册
tsc draft-inbox-event ...        # 草稿
tsc accept <draft> ...           # 确认
```

## 3. 建/同步记忆索引

```bash
tsc index-build          # 首次全量建索引（读 markdown → 向量 + 情绪）
tsc index-sync           # 增量同步（放进每小时 cron，取代全库重扫）
tsc index-stats          # 看索引规模/后端/维度
```

## 4. 查询（确定性，省 token）—— 这是 v2.0 的核心

```bash
# 语义搜索：找相似情况，不用 LLM 重读全库
tsc index-search "谁在交付上靠谱" --kind entity --topk 5
tsc index-search "GPU 采购 拖延" --kind event

# 身份解析：新建实体前先问索引有没有同一个人（杀 hash-ID / 名字漂移）
tsc identity-resolve "金老板" --topk 5

# 谁情绪不好：实体按情绪均值排序（负在前）
tsc index-mood
tsc index-mood --positive        # 反过来看谁状态好

# 僵尸行动：超 N 天没动 / 已逾期
tsc actions-stale --days 30
```

## 5. 单点工具（无需建索引也能用）

```bash
tsc emotion-score "已读不回真让人失望"      # {polarity,label,confidence,backend}
tsc text-segment "报价文档交付" --keywords  # jieba 关键词（缺 jieba 自动降级）
```

## 6. 判断与校准（OpenTSC 的灵魂）

```bash
tsc judgment-attribute p_carol execution_ceiling   # K7 据事件推导属性，不手填
tsc judgment-compare p_carol p_dave negotiation    # 谁更强，不重读历史

# 校准闭环 —— 把"度量别人"扭到"度量自己"
tsc stage-prediction ...     # 下一个带到期日的预测
tsc due                      # 今天到期、该验证的预测
tsc calibrate <id> --result correct|wrong|partial
tsc accuracy                 # 你的命中率账本（receipts）
```

## 7. 推荐的每日 cron 编排

| 时间 | 命令 | 作用 |
|---|---|---|
| 每小时 | `tsc index-sync` | 增量更新记忆，cron 之间不再各自全扫 |
| 早 | `tsc actions-stale --days 30` + `tsc due` | 清僵尸、列今日该验证的预测 |
| 晚 | `tsc index-mood` + `tsc accuracy` | 谁情绪差 + 自己判断准不准 |

> **铁律**：能用命令确定性回答的，就别让 LLM 重读 vault。详见 SKILL.md「CLI-first 强制约束」。

## 8. 切后端（要更准的情绪/向量）

编辑 `<vault>/soul/_config.yaml`：

```yaml
embedding_backend: local       # 换本地中文向量模型，语义更准
emotion_backend: model         # 换本地情绪模型，业务文本不再误判
```

切完跑一次 `tsc index-build` 重建（`index-sync` 也会自动检测并重建）。

## 9. 接入你自己的数据源（微信等）

采集器不在核心里——它们是**你自建的技能**，通过 CLI 喂数据。契约见
[`references/extending-with-skills.md`](../skill/references/extending-with-skills.md)。
