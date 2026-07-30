# 安全策略

## 支持的版本

| 版本   | 支持     |
|--------|----------|
| 1.0.x  | ✅       |
| < 1.0  | ❌ 请升级 |

## 报告漏洞

**请勿在公开 Issue 中披露安全漏洞。**

请通过以下方式私下报告：

1. 在 [GitHub Security Advisories](https://github.com/LZZZQ-Lab/enterprise-ai-agent/security/advisories/new) 提交 **Private vulnerability report**（推荐），或
2. 发送邮件至仓库维护者（在 GitHub 个人主页查看联系方式），标题：`[Security] enterprise-ai-agent`

请包含：

- 漏洞类型与影响范围
- 复现步骤或 PoC（尽量最小化）
- 受影响版本 / Commit
- 建议修复思路（如有）

我们将在 **72 小时内** 确认收到，并在修复发布前避免公开细节。

## 安全相关配置

生产环境建议启用（见 `backend/.env.example`）：

- `ENABLE_API_AUTH=true` — API Bearer / `X-API-Key`
- `ENABLE_INPUT_VALIDATION=true` — 输入长度与字符校验
- `ENABLE_PROMPT_INJECTION_GUARD=true` — Prompt 注入检测
- `ENABLE_DANGEROUS_TOOL_APPROVAL=true` — 危险 Tool 审批

切勿将 `.env`、密钥、`secret.yaml` 提交至 Git。

## 依赖安全

- [Dependabot](.github/dependabot.yml) 定期扫描 pip 与 GitHub Actions 依赖
- 合并依赖 PR 前请运行 `pytest -m "not integration"`
