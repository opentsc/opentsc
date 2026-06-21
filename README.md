<div align="center">

# OpenTSC — 壳 · 人际情报系统的运行容器

**把人对人际世界的隐性判断，变成显式、可查询、可审计、会自我进化的结构化情报系统。**

由 **dashen**（「AI 最严厉的父亲」）创立 · [dashen.wang](https://dashen.wang) · [@dashen_wang](https://x.com/dashen_wang)

[![License: AGPL v3](https://img.shields.io/badge/code-AGPL--3.0-blue.svg)](LICENSE) · [商用授权](LICENSING.md) · [魂 · 白皮书 →](https://github.com/opentsc/tsc)

</div>

---

> **TSC 是魂，OpenTSC 是壳。**
> 魂（[`opentsc/tsc`](https://github.com/opentsc/tsc) 白皮书）= 一套法 + 全部判断与记忆，决定"为什么存在、什么算好"。
> 壳（本仓）= 运行这套法的容器：模块 / agent / 技能，决定"怎么做"。
> 软件可重写、团队可换人、模型可升级——只要魂还在，这个 TSC 就还是同一个 TSC。

OpenTSC 是一个面向 Claude Code / Agent 的**单人、本地优先（local / offline-first）**人际情报系统——一间私人作战室，**不是 CRM**。

## 核心能力（v1.0）

- **事件图谱（K3）** — 事件是独立节点，多实体链接 + 因果边，当前状态由事件流推导而非手填。
- **判断引擎（K7，核心创新）** — 新事件到达，K7 读判断法典自动推导属性补丁；三层属性（base / skills / states），每条都是带 `{value, confidence, provenance, decay}` 的 AttributeClaim。
- **自创生引擎（K8）** — 检测能力缺口 → 生成 Agent 草稿 → 校验法则 → 用户审批激活。
- **11 个 VSM 职业** · **校准闭环**（预测→跟踪→命中率→法典自迭代）· **魂壳分离**（soul/ 可导出复活）。

## 快速开始

```bash
# 把本仓 skill/ 放到你项目的 .claude/skills/opentsc/，或直接用 CLI：
python skill/scripts/opentsc.py --root my-vault init
python skill/scripts/opentsc.py --root my-vault world-new-npc "Carol" --id p_carol --tag core_team
python skill/scripts/opentsc.py --root my-vault judgment-attribute p_carol execution_ceiling
```

完整命令见 [`skill/命令说明.md`](skill/命令说明.md) · 新手上路见 [`skill/新人使用教程.md`](skill/新人使用教程.md)。

## 魂 ↔ 壳 对照（理念如何被实现）

| 魂（白皮书法则） | 壳（实现） |
|---|---|
| 存在 1–3：创世不可变 / 魂壳分离 / 按 ID 立身 | `skill/scripts/opentsc_core/soul.py`、`identity.py`（K1）|
| 感知 4–6：事件只增 / 先证据后判断 / 先草稿后入册 | `events.py`（K3）· `references/data-contract.md` |
| 判断 7–9：双法典 / 现实校准 / 属性来自事件 | `judgment.py`（**K7**）· `judgment_codex_seed.md` |
| 进化 10–12：按需生长 / 四重自创生 / 递归同构 | `genesis_engine.py`（K8）· `professions.py` |

## 许可证 — 双许可

- **社区版**：[AGPL-3.0](LICENSE)。可自由使用/修改/分发；**改动及"做成在线服务"都须开源回馈**。
- **商业版**：需要闭源 / 商用而不想受 AGPL 约束？见 [LICENSING.md](LICENSING.md)，向 dashen 获取商业授权。
- **品牌**：OpenTSC™ / TSC™ / 薄壳公司™ 受商标保护，见 [TRADEMARK.md](TRADEMARK.md)。

贡献请先读 [CONTRIBUTING.md](CONTRIBUTING.md)（含 CLA）。

---

<div align="center">
OpenTSC · 创始人 dashen「AI 最严厉的父亲」· <a href="https://dashen.wang">dashen.wang</a> · <a href="https://x.com/dashen_wang">@dashen_wang</a>
</div>
