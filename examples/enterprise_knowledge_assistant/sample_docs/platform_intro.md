# 企业知识助手 Demo 样例文档

本产品为 Enterprise LLM Application Platform 的企业知识助手示例。

## 产品能力

- 上传 TXT / Markdown / PDF / DOCX 建立企业知识库
- Agent 通过 search_knowledge 工具检索相关内容
- LLM（OpenAI 兼容 / 本地 / vLLM）生成回答并返回引用来源

## 部署建议

生产环境建议使用 MODEL_PROVIDER=vllm，并配置 EMBEDDING_PROVIDER 与 VECTOR_STORE_PROVIDER=chroma。
