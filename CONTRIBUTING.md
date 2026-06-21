# 贡献指南 / Contributing

欢迎为 OpenTSC 贡献！在提交之前请阅读以下两点。

## 1. 贡献者许可协议（CLA）—— 必读

OpenTSC 采用**双许可**（AGPL-3.0 + 商业许可，见 [LICENSING.md](LICENSING.md)）。为使项目能持续以这两种方式分发，**所有贡献者必须同意以下 CLA**：

> 我保证我提交的贡献为我原创、我有权提交；我**将该贡献的版权以非独占、全球、永久、不可撤销的方式许可给项目创始人 dashen**，许可其以包括 AGPL-3.0 及商业许可在内的任何许可方式使用、修改、再许可与分发该贡献。我保留对自己贡献的著作权署名。

提交 Pull Request 即视为同意本 CLA。首次贡献请在 PR 描述中加一行：

```
I agree to the OpenTSC CLA.
```

我们也采用 [DCO](https://developercertificate.org/)：提交请带 `Signed-off-by`（`git commit -s`）。

## 2. 提交规范

- 改动前先看 [SECURITY.md](SECURITY.md)：**绝不提交任何真实个人数据**（姓名、聊天记录、联系方式）。示例一律用占位名（Carol / Dave / Eve / Acme）。
- 代码改动请确保 `python skill/tests/smoke.py` 通过。
- 遵守 OpenTSC 十二法则（见 `skill/references/philosophy.md`）；与法则冲突的改动会被拒绝。
- 保持术语一致：TSC=Thin-Shell Company=薄壳公司，魂/壳=Soul/Shell。

## 3. 行为准则

请友善、就事论事。骚扰、人身攻击不被接受。

---

有疑问联系 dashen · [dashen.wang](https://dashen.wang) · [@dashen_wang](https://x.com/dashen_wang)
