# Enterprise AI Platform — 系统架构

> **Enterprise AI Platform** 企业级大模型应用平台的系统设计说明。  
> 涵盖 Agent Runtime、Workflow、LLM 基础设施、RAG、模型Serving 与部署拓扑。  
> 目录结构见 [STRUCTURE.md](./STRUCTURE.md)；AI 软件团队应用层见 [software_team.md](./software_team.md)。

---

## 1. 总体架构

平台采用 **分层 + 模块化** 设计：上层应用通过 Canonical 包（`apps/`、`core/`、`llm/`、`knowledge/`）访问能力，实现位于 `backend/app/`，Legacy 路径 `app.*` 保持兼容。

### 1.1 逻辑分层

```mermaid
flowchart TB
    subgraph Presentation["表现 / 接入层"]
        REST["FastAPI REST / OpenAPI"]
        DASH["Infra Dashboard"]
        CLI["CLI / Demo Scripts"]
        FE["Vue Dashboard 前端"]
    end

    subgraph Application["应用层 backend/applications/"]
        ST["AI Software Team"]
        EKA["Enterprise Knowledge Assistant"]
        WF_DEMO["Workflow Demo"]
        MCP_D["MCP Demo"]
    end

    subgraph Platform["平台核心层"]
        subgraph Core["core/"]
            AG["Agent Runtime"]
            WF["Workflow Engine"]
            MEM["Memory"]
            TOOL["Tools / MCP"]
        end
        subgraph Knowledge["knowledge/"]
            RAG["RAG Pipeline"]
            EMB["Embedding"]
            VS["VectorStore"]
        end
        subgraph LLM_Layer["llm/"]
            PROV["Providers"]
            ROUTE["Router / Registry"]
            GW["Inference Gateway"]
        end
    end

    subgraph CrossCutting["横切能力"]
        PROMPT["Prompt Engineering"]
        OBS["Observability / Logging"]
        SEC["Security / Auth / Guard"]
        MON["Prometheus Metrics"]
    end

    subgraph Data["数据与外部系统"]
        VDB["Chroma / InMemory Vector DB"]
        REDIS["Redis"]
        EXT_LLM["OpenAI / DeepSeek / Azure"]
        VLLM["vLLM / Local LLM"]
    end

    FE --> REST
    CLI --> Application
    REST --> AG
    Application --> AG & WF & RAG
    AG --> PROV & TOOL & MEM & PROMPT
    WF --> AG & TOOL
    RAG --> EMB & VS & PROV
    PROV --> GW
    ROUTE --> PROV
    VS --> VDB
    GW --> EXT_LLM & VLLM
    REST --> SEC & OBS & MON
    AG --> REDIS
```

### 1.2 模块依赖原则

| 原则 | 说明 |
|------|------|
| **单向依赖** | 应用层 → 平台核心 → LLM/知识层；核心不依赖具体应用 |
| **配置驱动** | 统一 `Settings` + `.env`；`AgentConfig.from_env()` 注入运行时 |
| **Provider 抽象** | Agent 只依赖 `BaseLLM`，通过 Factory 切换 OpenAI / vLLM / Gateway |
| **可测试** | 248+ pytest；Mock LLM / Fake Embedding 支持离线验证 |
| **渐进迁移** | Canonical 包为 facade，实现仍在 `backend/app/`，零破坏升级 |

### 1.3 代码映射

| 架构层 | Canonical 路径 | 实现路径 |
|--------|----------------|----------|
| API 入口 | `apps/api` | `backend/app/main.py` |
| Agent | `core/agent` | `backend/app/agents/` |
| Workflow | `core/workflow` | `backend/app/workflow/` |
| Memory | `core/memory` | `backend/app/memory/` |
| Tools | `core/tools` | `backend/app/tools/` · `backend/app/mcp/` |
| RAG | `knowledge/rag` | `backend/app/rag/` |
| LLM | `llm/providers` | `backend/app/llm/` |
| Gateway | `llm/gateway` | `backend/app/gateway/` |
| Router | `llm/router` | `backend/app/router/` · `backend/app/model_registry/` |

---

## 2. Agent Runtime

Agent Runtime 是平台的 **执行内核**：接收任务、创建 Agent 实例、驱动 Prompt 构建与 Agent Loop，返回结构化结果。

### 2.1 组件关系

```mermaid
flowchart LR
    subgraph Input
        TASK["AgentTask<br/>session_id · message · history"]
    end

    subgraph Runtime["AgentRuntime"]
        REG["AgentRegistry"]
        FAC["AgentFactory"]
        SCH["AgentScheduler<br/>可选异步 Worker"]
    end

    subgraph Agent["BaseAgent 实现"]
        CHAT["ChatAgent"]
        MGR["ManagerAgent"]
        ST_A["Software Team Agents<br/>PM / Dev / Tester …"]
    end

    subgraph Execution["执行链"]
        PB["PromptBuilder"]
        EX["AgentExecutor<br/>Plan + ReAct Loop"]
        LLM["BaseLLM"]
        TM["ToolManager"]
        MM["MemoryManager"]
    end

    subgraph Output
        RES["AgentResult"]
    end

    TASK --> Runtime
    Runtime --> REG --> FAC --> Agent
    Agent --> PB --> EX
    EX --> LLM
    EX --> TM
    PB --> MM
    Agent --> RES
```

### 2.2 核心类型

| 组件 | 模块 | 职责 |
|------|------|------|
| `AgentTask` | `app/agents/runtime.py` | 任务描述：会话 ID、用户消息、历史、元数据 |
| `AgentRuntime` | `app/agents/runtime.py` | 注册表 + 工厂 + 调度；`run()` / `execute_task()` |
| `AgentRegistry` | `app/agents/registry.py` | Agent 类型注册与发现（`chat`、`developer` 等） |
| `AgentFactory` | `app/agents/factory.py` | 按名称与 `AgentConfig` 实例化 Agent |
| `AgentContext` / `AgentResult` | `app/agents/types.py` | 单次运行上下文与结果 |
| `AgentExecutor` | `app/agents/executor/` | LLM ↔ Tool 循环；Planner · Observation · Tracer |
| `ChatAgent` | `app/agents/chat_agent.py` | 默认对话 Agent（Plan + ReAct） |
| `PromptBuilder` | `app/prompts/builder.py` | System + Memory + Tools + User 消息组装 |

### 2.3 Agent Loop 时序

```mermaid
sequenceDiagram
    participant API as ChatService
    participant RT as AgentRuntime
    participant AG as ChatAgent
    participant PB as PromptBuilder
    participant EX as AgentExecutor
    participant LLM as BaseLLM
    participant TM as ToolManager
    participant MM as MemoryManager

    API->>RT: run(AgentTask)
    RT->>AG: run(AgentContext)
    AG->>PB: build(context)
    PB->>MM: load history / long-term
    PB-->>AG: messages[]
    AG->>EX: execute(messages, tools)
    loop Agent Loop (max MAX_AGENT_LOOP)
        EX->>LLM: chat(messages, tool_schemas)
        alt tool_calls
            LLM-->>EX: tool_calls[]
            EX->>TM: execute(tool, args)
            TM-->>EX: ToolResult
            EX->>EX: append tool observation
        else final answer
            LLM-->>EX: content
            EX-->>AG: AgentLoopResult
        end
    end
    AG->>MM: after_run(persist)
    AG-->>RT: AgentResult
    RT-->>API: AgentResult
```

### 2.4 Multi-Agent 扩展

Software Team 等多 Agent 场景在 `app/agents/software_team/` 注册独立角色 Agent，由 **ManagerAgent** 动态规划任务列表，经同一 `AgentRuntime` 调度各专家 Agent，共享 `shared_context` 与 `ProjectMemory`。

---

## 3. Workflow Engine

Workflow Engine 提供 **可配置 DAG** 编排：支持 Agent 节点、Tool 节点、条件分支与人工审批（Human-in-the-loop），通过 `AgentRuntime` 调用 Agent，不修改 Runtime 本身。

### 3.1 引擎结构

```mermaid
flowchart TB
    subgraph Definition["工作流定义"]
        G["WorkflowGraph"]
        N["WorkflowNode<br/>AGENT · TOOL · CONDITION · HUMAN"]
        E["WorkflowEdge<br/>条件表达式"]
        REG_W["WorkflowRegistry"]
    end

    subgraph Execution["WorkflowExecutor"]
        TOPO["拓扑排序 / 分支解析"]
        STATE["WorkflowExecutionContext<br/>variables · node_outputs"]
        HUMAN["HumanApprovalNode<br/>暂停 · 恢复 · 拒绝"]
        FAIL["OnFailureAction<br/>retry · skip · abort"]
    end

    subgraph Integrations["集成"]
        RT2["AgentRuntime"]
        TE["ToolExecutor"]
    end

    REG_W --> G
    G --> N & E
    G --> Execution
    Execution --> RT2 & TE
    HUMAN -.->|await approval| Execution
```

### 3.2 节点类型

| `NodeType` | 行为 |
|------------|------|
| `AGENT` | 构造 `AgentTask`，调用 `AgentRuntime.run()` |
| `TOOL` | 经 `ToolExecutor` 执行注册 Tool |
| `CONDITION` | 评估边表达式，选择下一分支 |
| `HUMAN` | 暂停工作流，等待人工审批 API 恢复 |

### 3.3 状态机

```mermaid
stateDiagram-v2
    [*] --> RUNNING
    RUNNING --> PAUSED: Human Approval 节点
    PAUSED --> RUNNING: approve / reject 回调
    RUNNING --> COMPLETED: 所有节点完成
    RUNNING --> FAILED: 不可恢复错误
    RUNNING --> CANCELLED: 用户取消
    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

关键模块：`app/workflow/graph.py` · `executor.py` · `human_node.py` · `registry.py`

---

## 4. LLM Infrastructure

LLM 基础设施层负责 **模型接入、路由、网关与可观测性**，对上层 Agent 暴露统一的 `BaseLLM` 接口。

### 4.1 基础设施全景

```mermaid
flowchart TB
    subgraph Consumers["消费者"]
        AG2["AgentExecutor"]
        RAG_LLM["RAGPipeline.ask()"]
        GW_API["/api/v1/inference/*"]
    end

    subgraph Factory["LLM Factory"]
        F["create_llm_provider()<br/>MODEL_PROVIDER 驱动"]
    end

    subgraph Providers["llm/providers"]
        OAI["OpenAIProvider<br/>OpenAI / DeepSeek / Azure"]
        VLLM_P["VLLMProvider<br/>自托管 vLLM"]
        LOC["LocalLLMProvider<br/>进程内 Qwen"]
        GW_P["GatewayLLMProvider<br/>经 Gateway 代理"]
    end

    subgraph Gateway["llm/gateway — Inference Gateway"]
        IGW["InferenceGateway"]
        STATS["Token Stats"]
        LOG_G["Request / Response Log"]
        BACK["Backend Adapter<br/>openai · vllm · sglang · tgi"]
    end

    subgraph Router["llm/router"]
        REG_M["Model Registry<br/>models.yaml 元数据"]
        RE["RouterEngine<br/>TaskKind · Cost · Latency"]
    end

    subgraph External["外部推理服务"]
        API_E["云端 API"]
        VLLM_S["vLLM Server :8000"]
        GPU["GPU Manager<br/>显存 · 调度快照"]
    end

    AG2 --> F
    RAG_LLM --> F
    F --> Providers
    F --> GW_P --> IGW
    IGW --> BACK
    BACK --> API_E & VLLM_S
    RE --> REG_M
    RE -.->|选模建议| F
    GW_API --> IGW
    GPU -.-> MON2["Infra Metrics"]
```

### 4.2 Provider 矩阵

| Provider | 配置 | 场景 |
|----------|------|------|
| `openai` | `API_KEY` · `OPENAI_BASE_URL` · `MODEL_NAME` | 云端 API、DeepSeek 等兼容接口 |
| `vllm` | `VLLM_ENDPOINT` · `VLLM_MAX_TOKENS` | 企业自托管 GPU 推理 |
| `local` | `MODEL_NAME`（Qwen 等） | 开发 / 离线 Transformers |
| `gateway` | `ENABLE_INFERENCE_GATEWAY=true` | 统一网关、Token 统计、多后端 |

### 4.3 Model Registry & Router

- **Model Registry**（`app/model_registry/`）：YAML 驱动模型元数据（Vendor · Cost · Context Window · Capability Tags）
- **RouterEngine**（`app/router/engine.py`）：根据 `TaskKind`（CHAT / CODE / RAG / LONG_CONTEXT 等）、Cost、Latency 策略从 Registry 选择最优模型

```mermaid
flowchart LR
    CTX["RoutingContext<br/>prompt · task · budget"]
    CLS["Task Classifier"]
    POL["RoutePolicy"]
    REG2["ModelRegistryManager"]
    REP["RoutingReport<br/>selected_model · candidates"]

    CTX --> CLS --> POL
    POL --> REG2 --> REP
```

---

## 5. RAG Pipeline

RAG 子系统实现 **企业文档入库 → 向量检索 → 上下文注入 → LLM 生成 → 来源引用** 的完整闭环。

### 5.1 Pipeline 架构

```mermaid
flowchart TB
    subgraph Ingest["入库路径 ingest"]
        UP["POST /knowledge/documents"]
        LD["DocumentLoader<br/>.md · .txt · .pdf"]
        SP["DocumentSplitter<br/>Chunk 策略"]
        KB["KnowledgeBase.add()"]
        EMB2["EmbeddingProvider"]
        VS2["VectorStore<br/>Chroma / InMemory"]
    end

    subgraph Query["问答路径 ask"]
        Q["POST /knowledge/ask"]
        RET["Retriever<br/>Top-K · Score Threshold"]
        CB["RAGContextBuilder<br/>Prompt 模板"]
        LLM2["BaseLLM"]
        ANS["RAGAnswer<br/>answer + sources[]"]
    end

    subgraph AgentPath["Agent 集成"]
        SKT["SearchKnowledgeTool"]
        CHAT2["ChatAgent + Tool Loop"]
    end

    UP --> LD --> SP --> KB
    KB --> EMB2 --> VS2
    Q --> RET
    VS2 --> RET
    RET --> CB --> LLM2 --> ANS
    SKT --> RET
    CHAT2 --> SKT
```

### 5.2 核心类

| 类 | 路径 | 职责 |
|----|------|------|
| `RAGPipeline` | `app/rag/pipeline.py` | 统一入口：`ingest_file()` · `ask()` |
| `KnowledgeBase` | `app/rag/knowledge_base.py` | Chunk 写入与检索 facade |
| `Retriever` | `app/rag/retriever.py` | 相似度检索 + 分数过滤 |
| `RAGContextBuilder` | `app/rag/context_builder.py` | 检索结果 → LLM Prompt |
| `SearchKnowledgeTool` | `app/tools/knowledge_tool.py` | Agent Tool 形式暴露 RAG |

### 5.3 配置项

```env
EMBEDDING_PROVIDER=fake          # fake | local | openai
VECTOR_STORE_PROVIDER=memory     # memory | chroma
ENABLE_KNOWLEDGE_TOOL=true
KNOWLEDGE_UPLOAD_DIR=./data/knowledge_uploads
```

---

## 6. Model Serving

模型 Serving 层描述 **推理服务如何部署、暴露与扩展**。

### 6.1 Serving 拓扑

```mermaid
flowchart TB
    subgraph Client["调用方"]
        APP["Enterprise AI API :8001"]
        DIRECT["外部 OpenAI SDK 客户端"]
    end

    subgraph ServingOptions["Serving 模式"]
        subgraph Cloud["模式 A — 云端 API"]
            OAI_API["OpenAI / DeepSeek / Azure"]
        end

        subgraph SelfHosted["模式 B — 自托管 vLLM"]
            VLLM_C["vLLM Container<br/>OpenAI Compatible :8000"]
            HF["HF Model Cache Volume"]
            GPU_N["NVIDIA GPU"]
        end

        subgraph GatewayMode["模式 C — Inference Gateway"]
            GW_S["InferenceGateway Service"]
            ADAPT["Backend Adapters"]
        end
    end

    subgraph Ops["运维能力"]
        CACHE["Model Cache Layer<br/>Redis / Memory"]
        SD["Service Discovery"]
        HPA["HPA 自动扩缩容"]
        BENCH["LLM Benchmark<br/>TTFT · Throughput"]
    end

    APP --> Cloud & SelfHosted & GatewayMode
    DIRECT --> VLLM_C
    VLLM_C --> GPU_N & HF
    GW_S --> ADAPT --> Cloud & SelfHosted
    APP --> CACHE & SD
    SelfHosted --> HPA
```

### 6.2 vLLM Serving 要点

| 项 | 说明 |
|----|------|
| 镜像 | `vllm/vllm-openai`（Compose / K8s 清单内置） |
| 协议 | OpenAI Compatible REST（`/v1/chat/completions`） |
| 平台对接 | `VLLMProvider` → `VLLM_ENDPOINT=http://llm:8000/v1` |
| 调优 | `VLLM_MAX_LEN` · `VLLM_GPU_UTIL` · `--enforce-eager` 等 |
| 基准 | `backend/benchmark/` — Qwen / vLLM / OpenAI 对比报告 |

### 6.3 Gateway Serving 要点

`InferenceGateway` 在 Provider 之上提供：

- 统一 `request_id` 与结构化请求/响应日志
- Token 用量统计（`get_token_stats()`）
- 多后端适配（OpenAI 兼容、vLLM、SGLang、TGI）
- 异常映射与可观测性钩子

启用方式：`ENABLE_INFERENCE_GATEWAY=true` 或 `MODEL_PROVIDER=gateway`

---

## 7. Data Flow

### 7.1 对话请求数据流

```mermaid
sequenceDiagram
    participant U as 用户 / Client
    participant N as Nginx
    participant API as FastAPI
    participant SEC as Security
    participant CS as ChatService
    participant RT as AgentRuntime
    participant LLM as LLM Provider
    participant OBS as Observability

    U->>N: POST /api/v1/chat
    N->>API: proxy
    API->>SEC: Auth · Input Validation · Injection Guard
    SEC->>CS: sanitized message
    CS->>OBS: set session_id / agent_id
    CS->>RT: AgentTask
    RT->>LLM: chat completions (可能多轮 Tool)
    LLM-->>RT: AgentResult
    RT-->>CS: result
    CS->>OBS: token · latency · metrics
    CS-->>API: ChatResponse
    API-->>U: JSON answer
```

### 7.2 知识问答数据流

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as Knowledge API
    participant RAG as RAGPipeline
    participant VS as VectorStore
    participant LLM as BaseLLM

    Note over U,VS: 入库阶段
    U->>API: POST /knowledge/documents (file)
    API->>RAG: ingest_file()
    RAG->>VS: upsert embeddings

    Note over U,LLM: 问答阶段
    U->>API: POST /knowledge/ask
    API->>RAG: ask(question)
    RAG->>VS: similarity search
    VS-->>RAG: scored chunks + sources
    RAG->>LLM: prompt + context
    LLM-->>RAG: answer
    RAG-->>API: RAGAnswer
    API-->>U: answer + sources[]
```

### 7.3 Software Team 全链路数据流（摘要）

```mermaid
flowchart LR
    REQ["用户需求"] --> PM["ManagerAgent<br/>任务规划"]
    PM --> P1["Product → PRD"]
    P1 --> P2["Architecture → Design"]
    P2 --> P3["Developer → Code"]
    P3 --> P4["Reviewer → Review Report"]
    P4 --> P5["Tester → pytest Report"]
    P5 --> P6["DevOps → Deploy Report"]
    P6 --> OUT["project_runs/{run_id}/<br/>reports · workspace · logs"]
```

详细角色、Tool 约束与 Demo 命令见 [software_team.md](./software_team.md)。

### 7.4 可观测性数据流

| 信号 | 产生位置 | 消费 |
|------|----------|------|
| 结构化 JSON 日志 | `observability/logging/` | ELK / Loki |
| Prometheus 指标 | `app/monitoring/` · `/metrics` | Grafana |
| Agent Trace | `app/agents/executor/tracer.py` | Dashboard / Debug |
| Gateway Token | `app/gateway/stats.py` | Infra Dashboard |

---

## 8. Deployment Architecture

平台支持 **轻量开发栈**、**生产 Compose 全栈** 与 **Kubernetes 企业部署** 三档拓扑。

### 8.1 部署模式对比

| 模式 | 路径 | 组件 | 适用场景 |
|------|------|------|----------|
| 本地开发 | `backend/` + uvicorn | API only | 日常开发、单元测试 |
| 轻量 Docker | `infra/docker/` | API ± vLLM | Swagger Demo、无 GPU 仅 API |
| 生产 Compose | `infra/deploy/` | Nginx + API + Agent + vLLM + Chroma + Redis | 单机 / 小集群生产 |
| Kubernetes | `infra/k8s/` | Deployment + Ingress + HPA + PVC | 企业 K8s 集群 |

### 8.2 生产 Compose 拓扑

```mermaid
flowchart TB
    subgraph Internet["外部访问"]
        USER["Client / Browser"]
    end

    subgraph Host["Docker Host :8080"]
        NG["nginx :80<br/>反向代理 · 超时 · 大文件"]
        API["api :8001<br/>FastAPI + AgentRuntime"]
        AGW["agent worker<br/>Redis 心跳 / 队列预留"]
    end

    subgraph Backend_Services["后端服务"]
        VLLM["vllm :8000<br/>GPU · OpenAI API"]
        CHROMA["chroma<br/>Vector DB + PVC"]
        REDIS["redis<br/>Cache / Queue"]
    end

    subgraph Volumes["持久化"]
        HF["hf-cache"]
        CHROMA_V["chroma-data"]
        KNOW["knowledge uploads"]
    end

    USER --> NG --> API
    API --> VLLM & CHROMA & REDIS
    AGW --> REDIS
    VLLM --> HF
    CHROMA --> CHROMA_V
    API --> KNOW
```

> Agent 推理主路径在 **API 进程**内同步执行；`agent` Worker 用于企业化拆分与后续水平扩展。

### 8.3 Kubernetes 拓扑

```mermaid
flowchart TB
    subgraph K8s["Kubernetes Cluster"]
        ING["Ingress<br/>TLS · 路由"]
        SVC_API["Service: api"]
        SVC_VLLM["Service: vllm"]
        SVC_CHROMA["Service: chroma"]
        SVC_REDIS["Service: redis"]

        DEP_API["Deployment: api<br/>replicas · HPA"]
        DEP_VLLM["Deployment: vllm<br/>nvidia.com/gpu"]
        DEP_CHROMA["StatefulSet/PVC: chroma"]
        DEP_REDIS["Deployment: redis"]

        CM["ConfigMap"]
        SEC_K["Secret"]
    end

    CLIENT["Enterprise Client"] --> ING
    ING --> SVC_API --> DEP_API
    DEP_API --> SVC_VLLM & SVC_CHROMA & SVC_REDIS
    DEP_VLLM --> SVC_VLLM
    CM & SEC_K -.-> DEP_API & DEP_VLLM
```

清单目录：`infra/k8s/`（namespace · configmap · secret · api · vllm · chroma · redis · ingress · hpa · kustomization）

### 8.4 CI/CD 与镜像

```mermaid
flowchart LR
    PUSH["git push"] --> CI["GitHub Actions<br/>test.yml"]
    CI --> LINT["ruff lint"]
    CI --> PYTEST["pytest -m not integration"]
    CI --> COMPOSE["Compose config validate"]
    CI --> OAI["OpenAPI export + VERSION check"]
    CI -->|success| BUILD["build.yml<br/>Docker build"]
    BUILD --> IMG1["infra/docker/Dockerfile<br/>api:ci"]
    BUILD --> IMG2["infra/deploy/Dockerfile<br/>deploy:ci"]
```

| 镜像 | Dockerfile | 用途 |
|------|------------|------|
| 开发 / 轻量 API | `infra/docker/Dockerfile` | API + Canonical 包 |
| 生产 API | `infra/deploy/Dockerfile` | API + knowledge 依赖 + Redis |

### 8.5 环境变量分层

```text
┌─────────────────────────────────────────┐
│  .env / ConfigMap / Secret              │
│  MODEL_PROVIDER · API_KEY · VLLM_*      │
│  EMBEDDING_PROVIDER · VECTOR_STORE_*  │
│  ENABLE_API_AUTH · ENABLE_*_GUARD      │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  app/config/settings.py (Pydantic)       │
└─────────────────┬───────────────────────┘
                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ AgentConfig  │  │ LLM Factory  │  │ RAG Pipeline │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [STRUCTURE.md](./STRUCTURE.md) | 目录结构与 Canonical / Legacy 映射 |
| [software_team.md](./software_team.md) | AI 软件团队 Agent 与应用层 Demo |
| [production_deploy.md](./production_deploy.md) | 生产 Compose 启动与运维 |
| [deployment.md](./deployment.md) | 轻量 Docker 栈 |
| [vllm_deployment.md](./vllm_deployment.md) | vLLM 安装与联调 |
| [infra/k8s/README.md](../infra/k8s/README.md) | Kubernetes 部署步骤 |
| [API.md](./API.md) | REST API 参考 |

---

<p align="center"><sub>Enterprise AI Platform Architecture · v1.0.0</sub></p>
