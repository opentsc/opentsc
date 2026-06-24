<div align="center">

# OpenTSC

**一个本地、私密的"记忆库"——帮你记住你打交道的人、手上的项目、做过的决定，还会回头帮你核对：你当初的判断到底准不准。**

[English](README.md) · 🌐 **中文**

由 **dashen**（「AI 最严厉的父亲」）创立 · [dashen.wang](https://dashen.wang) · [@dashen_wang](https://x.com/dashen_wang)

[![License: AGPL v3](https://img.shields.io/badge/code-AGPL--3.0-blue.svg)](LICENSE) · ![version](https://img.shields.io/badge/version-v2.1.0-green.svg) · [商用授权](LICENSING.md) · [白皮书（魂）→](https://github.com/opentsc/tsc)

[更新日志](CHANGELOG.md) · [迁移 v1→v2](MIGRATION.md) · [使用说明](docs/usage.md)

</div>

---

## OpenTSC 是什么？

你每天要应付一堆人和一堆事。笔记到处散、脑子记不全，而且你几乎从不回头看自己当初的判断对没对。OpenTSC 就是来补这个：

- 📝 **你随手记下发生了什么** —— "Carol 按时交了报价"、"Dave 又在拖 GPU 采购"。
- 🗂️ **它把这些整理成一个可搜索的记忆库** —— 每条信息都标注来源和可信度。
- 💬 **你用大白话问它** —— *谁交付最靠谱？这种情况我以前遇到过吗？我还在等谁的什么？*
- 🎯 **你记下预测，它过后告诉你命中率** —— 让你的判断力真的在变好，而不是悄悄飘走。
- 🔒 **所有数据都留在你自己电脑上。** 本地优先、单人使用、不上云、不要账号。

它**不是 CRM**（它管的是判断和决策，不是存通讯录），也不是社交软件。把它当成一个**为你的工作关系和事务服务的"第二大脑"**——一个会拿现实结果来跟你对账的第二大脑。

## 你具体能拿它干嘛？

| 你想… | 用大白话说 → 它执行 |
|---|---|
| 记一件发生的事，带证据 | "记一下 Carol 按时交付了" → `event-add` |
| 按**意思**找人/找类似情况（不是关键词） | "谁交付靠谱？" → `index-search` |
| 别把同一个人重复建档 | "已经有 Mike 了吗？" → `identity-resolve` |
| 看哪些事过期/烂尾了 | "我的待办里哪些在发霉？" → `actions-stale` |
| 给自己的预测打分、看命中率 | `stage-prediction` → `calibrate` → `accuracy` |
| 从自己的记录里看出规律 | "最近谁状态不好？" → `index-mood` |

> 示例都用占位名（Carol、Dave…）。**OpenTSC 不含任何真实数据。** 请合法、负责任地使用，只处理你有权持有的信息——见 [SECURITY.md](SECURITY.md)。

## 它怎么运作（30 秒看懂）

OpenTSC 是一个**给 AI 编程助手用的技能**（Claude Code 等）+ 一个 **Python 命令行工具**。你通过 AI 助手用大白话跟它说话；它把一切存成**你自己拥有的 Markdown 文件**，并在上面建一个快速的语义搜索索引。

```bash
python skill/scripts/opentsc.py --root my-vault init
python skill/scripts/opentsc.py --root my-vault event-add B2 "Carol 按时交了报价" "会议纪要" --link p_carol
python skill/scripts/opentsc.py --root my-vault index-search "谁靠谱" --kind entity
```

可选增强（全部按需开启，核心零依赖也能跑）：中文分词（jieba）、情绪打分（词典/本地模型/大模型）、向量记忆索引（zvec）。见[使用说明](docs/usage.md)。

## 快速开始

> **zvec 索引需 Python 3.10–3.14**（核心本身裸 Python 即可跑）。macOS 自带 Python 是 3.9、或遇到 `externally-managed-environment`(PEP 668),请用 **uv**——完整步骤见 **[INSTALL.md](INSTALL.md)**。

```bash
# 1. 作为 skill 安装 —— 仓库的 skill/ 子目录才是 skill,不是仓库根目录
git clone https://github.com/opentsc/opentsc
cp -r opentsc/skill ~/.claude/skills/opentsc        # 或 ~/.hermes/skills/opentsc

# 2.(可选)开启记忆引擎 —— 推荐 Tier-1 后端
uv venv ~/.venvs/opentsc --python 3.11 && source ~/.venvs/opentsc/bin/activate
uv pip install jieba snownlp zvec
cp opentsc/skill/templates/_config.yaml <你的vault>/soul/_config.yaml
```

然后看[使用说明](docs/usage.md) · 安装细节见 [INSTALL.md](INSTALL.md) · 从 v1.0 升级看 [MIGRATION.md](MIGRATION.md)(数据不用改)。

## 背后更大的想法

OpenTSC 是一个叫 **TSC（薄壳公司）** 的概念的**"壳"**：讲*一个人*怎么靠 AI agent 驱动一个大而能自我进化的组织。一句话精华：

> 把你的**判断力和记忆**（"魂"）和运行它的软件/团队/AI 模型（"壳"）分开——这样换任何工具，它都死不了。把魂导出，就等于把整个组织搬走了。

完整理论在[白皮书（魂）仓库](https://github.com/opentsc/tsc)。每条理念对应哪段代码，见 [SKILL.md](skill/SKILL.md)。

## 许可证

- **代码**：社区版 [AGPL-3.0](LICENSE)；闭源商用可买[商业授权](LICENSING.md)。
- **名字与品牌**：OpenTSC™ / TSC™ 为商标，见 [TRADEMARK.md](TRADEMARK.md)。
- 贡献：见 [CONTRIBUTING.md](CONTRIBUTING.md)（含 CLA）。

---

<div align="center">
OpenTSC · 创始人 dashen「AI 最严厉的父亲」· <a href="https://dashen.wang">dashen.wang</a> · <a href="https://x.com/dashen_wang">@dashen_wang</a>
</div>
