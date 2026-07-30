# Enterprise AI Platform — 技术博客

Phase 9 技术文章系列，基于平台真实实现撰写。每篇包含：**背景 · 问题 · 方案 · 实现 · 总结**。

| # | 文章 | 主题 | 相关 Demo |
|---|------|------|-----------|
| 01 | [Agent 架构设计](./01-Agent架构设计.md) | Runtime · Executor · Registry | [demo_03](../../examples/demo_03_agent.py) |
| 02 | [vLLM 部署实践](./02-vLLM部署实践.md) | 自托管推理 · Docker · 联调 | [vllm_deployment.md](../vllm_deployment.md) |
| 03 | [RAG 系统设计](./03-RAG系统设计.md) | 入库 · 检索 · Agent Tool | [demo_02](../../examples/demo_02_rag.py) |
| 04 | [Multi-Agent 协作](./04-Multi-Agent协作.md) | 角色注册 · 共享上下文 · Workflow | [demo_04](../../examples/demo_04_workflow.py) |
| 05 | [AI Software Team 实现](./05-AI-Software-Team实现.md) | 七角色流水线 · 落盘规范 | [demo_05](../../examples/demo_05_software_team.py) |
| 06 | [LLM Infra 设计](./06-LLM-Infra设计.md) | Gateway · Router · Registry | [demo_06](../../examples/demo_06_infra.py) |

## 阅读顺序建议

**入门：** 01 → 03 → 02  
**Multi-Agent / 软件团队：** 04 → 05  
**生产与治理：** 02 → 06  

## 相关文档

- [系统架构](../architecture.md)
- [目录结构](../STRUCTURE.md)
- [Demo 体系](../../examples/README.md)
- [主 README](../../README.md)
