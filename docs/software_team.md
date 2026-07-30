# AI 软件工程团队（Phase 5）

本文档描述 **Enterprise LLM Application Platform** 在 Phase 5 交付的 **AI 软件团队**：平台层 Agent（`backend/app/agents/software_team/`）、Tool 约束、Prompt 模板，以及 **Task 5.8** 端到端 Demo 与 `project_runs/` 运行记录。

> 应用层历史流水线（Workspace / Git / Verification）见 [software_team_pipeline.md](./software_team_pipeline.md) 与 `backend/applications/software_team/`。

---

## 1. 目标与分层

| 层级 | 路径 | 职责 |
|------|------|------|
| **平台 Agent** | `app/agents/software_team/` | 可注册到 `AgentRegistry`、由 `AgentRuntime` 调度的角色 Agent |
| **Prompt 模板** | `app/prompts/templates/software_team_*.txt` | 各角色 LLM 指令，禁止在代码中硬编码长 Prompt |
| **应用 Demo / 编排** | `applications/software_team/` | 单角色 Demo、`pipeline/` 全链路、`project_runs/` 落盘 |
| **应用流水线（P5 早期）** | `applications/software_team/workflow/` | Coordinator、Git、Execution（与平台 Agent 可并存、逐步对齐） |

设计原则：

- **Manager** 用 LLM **动态规划**任务，不硬编码固定六步流水线（无 LLM 时有 fallback 任务列表）。
- **Developer / Tester / DevOps** 的文件变更与命令执行 **必须经 Tool**（LLM 不得在正文中“假写”文件或执行 shell）。
- 各专家 Agent 可单独 Demo，也可由 **SoftwareTeamPipeline** 串联。

---

## 2. Agent 一览

| 注册名 | 类 | Task | 输入 | 输出 |
|--------|-----|------|------|------|
| `project_manager` | `ProjectManagerAgent` | 5.1 | 用户需求 | 任务列表 + `SoftwareProject` |
| `product` | `ProductRequirementAgent` | 5.2 | 需求 / PRD 上下文 | 完整 PRD（Markdown） |
| `architecture` | `ArchitectureAgent` | 5.3 | PRD | System Design / `architecture.md` |
| `developer` | `DeveloperAgent` | 5.4 | 架构 + 任务 | 工作区代码 + Code Change History |
| `reviewer` | `ReviewerAgent` | 5.5 | Git Diff | Review Report |
| `tester` | `TesterAgent` | 5.6 | 工作区源码 | Test Report（pytest） |
| `devops` | `DevOpsAgent` | 5.7 | 工作区 | Deployment Report |

已在 `app/agents/__init__.py` 注册：`product`、`architecture`、`developer`、`reviewer`、`tester`、`devops`（Manager 通过 `ProjectManagerAgent` 直接实例化，name 为 `project_manager`）。

### 2.1 Project Manager（5.1）

- **模块**：`manager_agent.py`、`workflow.py`、`task.py`
- **流程**：理解目标 → LLM 规划 JSON 任务数组 → `SoftwareProject`
- **Task 字段**：`id`, `title`, `description`, `agent`, `status`, `result`
- **可选**：`metadata["execute_tasks"]=True` + 注入 `AgentRuntime` 按任务调用各 Agent

```powershell
python -m applications.software_team.run_pm_demo --requirement "开发一个博客系统"
```

### 2.2 Product（5.2）

- **模块**：`product_agent.py`、`prd_prompt.py`
- **模板**：`software_team_prd.txt`
- **RAG**：`enable_rag` + `retriever` 注入企业规范
- **章节约束**：功能需求、用户角色、业务流程、API 需求

```powershell
python -m applications.software_team.run_product_demo
```

### 2.3 Architecture（5.3）

- **模块**：`architecture_agent.py`、`architecture_prompt.py`
- **模板**：`software_team_architecture.txt`
- **输出章节**：系统架构、技术选型、数据库设计、接口设计
- **落盘**：`metadata["artifact_dir"]` → `docs/architecture.md`

```powershell
python -m applications.software_team.run_architecture_demo --write ./tmp-arch-demo
```

### 2.4 Developer（5.4）

- **模块**：`developer_agent.py`、`developer_tool_manager.py`、`code_change_history.py`
- **Tools**：
  - `filesystem`：只读 `read` / `list`
  - `code`：唯一写文件入口（`write` / `search_replace` / `append`）
- **约束**：检测到 LLM 在回复中贴大段代码且无 Tool Call 时会拒绝
- **历史**：`.software_team/code_change_history.jsonl`

```powershell
python -m applications.software_team.run_developer_demo --workspace ./tmp-dev-demo
```

### 2.5 Reviewer（5.5）

- **模块**：`reviewer_agent.py`、`review_report.py`、`reviewer_heuristics.py`
- **模板**：`software_team_reviewer.txt`
- **输入**：`metadata["git_diff"]` / `git_diff_path` / `use_git_diff` + `workspace_dir`
- **审查维度**：代码规范、安全、性能、架构 + **修改建议汇总**
- **Fallback**：无 LLM 时启发式扫描 Diff

```powershell
python -m applications.software_team.run_reviewer_demo
```

### 2.6 Tester（5.6）

- **模块**：`tester_agent.py`、`test_report.py`、`tester_tool_manager.py`
- **Tools**：`filesystem` + `code`（写测试）+ `terminal`（**仅 pytest**）
- **模板**：`software_team_tester.txt`
- **流程**：LLM Loop 写测试 → Agent 收尾 **强制再跑一轮 pytest** → Test Report

```powershell
python -m applications.software_team.run_tester_demo --workspace ./tmp-tester-demo
```

Terminal 模式：`terminal_mode_ctx` = `pytest`（Tester）或 `devops`（DevOps）。

### 2.7 DevOps（5.7）

- **模块**：`devops_agent.py`、`deployment_report.py`、`devops_tool_manager.py`
- **Tools**：`filesystem`、`code`（Dockerfile / compose）、`environment`（**.env.example** 等，禁止写 `.env` 密钥）、`terminal`（**docker build / docker compose**）
- **模拟部署**：`metadata["devops_simulate"]=True` 或本机无 Docker 时自动模拟 Build/Deploy 日志

```powershell
python -m applications.software_team.run_devops_demo --workspace ./tmp-devops-demo
```

---

## 3. 端到端 Demo（Task 5.8）

**入口**：`applications/software_team/run_full_team_demo.py`  
**编排**：`applications/software_team/pipeline/team_pipeline.py` · `SoftwareTeamPipeline`

### 3.1 场景

用户输入：**「开发一个用户管理系统」**

固定阶段顺序（与 PM 拆分的任务列表一致，Demo 按工程顺序执行）：

```
Manager → Product → Architecture → Developer → Reviewer → Tester → DevOps
```

Demo 默认使用 **用户管理系统** 主题的 Mock LLM（`pipeline/demo_clients.py`）；Developer / Reviewer / Tester / DevOps 在无 LLM 或 fallback 路径下仍可跑通，便于 CI 与离线演示。

### 3.2 运行

```powershell
cd backend
python -m applications.software_team.run_full_team_demo
python -m applications.software_team.run_full_team_demo --requirement "开发一个用户管理系统"
python -m applications.software_team.run_full_team_demo --runs-dir ../project_runs
```

默认运行记录目录：`backend/project_runs/{run_id}/`。

### 3.3 `project_runs/` 结构

```
project_runs/{run_id}/
├── tasks.json                 # Manager 输出的 SoftwareProject
├── run_manifest.json          # 阶段时间线、路径索引
├── logs/
│   ├── 01_manager_project_manager.json
│   ├── 02_product_product.json
│   └── …                      # 每阶段 success/model/完整 content
├── reports/
│   ├── MANAGER_TASK_LIST.md
│   ├── PRD.md
│   ├── architecture.md
│   ├── developer_summary.md
│   ├── REVIEW_REPORT.md
│   ├── TEST_REPORT.md
│   ├── DEPLOYMENT_REPORT.md
│   └── PIPELINE_SUMMARY.md
└── workspace/                 # 工程工作区（docs、src、tests、Docker 等）
```

### 3.4 阶段间上下文

`SoftwareTeamPipeline` 通过 `shared_context` 传递：

- `project_name`、`goal_summary`、`tasks`
- `prd`、`architecture`
- 各阶段报告摘要（供后续 Agent 只读）

工作区路径：`metadata["workspace_dir"]` = `{run_root}/workspace`。

---

## 4. Runtime 调用示例

```python
from app.agents.runtime import AgentRuntime, AgentTask
from app.config import AgentConfig

runtime = AgentRuntime(default_config=AgentConfig(enable_trace=False))

result = runtime.run(
    AgentTask(
        session_id="my-session",
        agent_name="product",
        user_message="开发一个用户管理系统",
        shared_context={"goal_summary": "..."},
    ),
    client=your_llm_client,  # 工厂 kwargs 注入对应 Agent
)
```

Developer / Tester / DevOps 需额外设置：

```python
metadata={
    "workspace_dir": "/path/to/workspace",
    "devops_simulate": True,   # DevOps 可选
}
```

---

## 5. 测试

| 测试文件 | 覆盖 |
|----------|------|
| `tests/test_software_team_pm.py` | 5.1 PM |
| `tests/test_software_team_product.py` | 5.2 Product |
| `tests/test_software_team_architecture.py` | 5.3 Architecture |
| `tests/test_software_team_developer.py` | 5.4 Developer |
| `tests/test_software_team_reviewer.py` | 5.5 Reviewer |
| `tests/test_software_team_tester.py` | 5.6 Tester |
| `tests/test_software_team_devops.py` | 5.7 DevOps |
| `tests/test_software_team_full_pipeline.py` | 5.8 全链路 |

```powershell
cd backend
python -m pytest tests/test_software_team_*.py -q
```

---

## 6. 与架构文档的关系

- **[architecture.md](./architecture.md)**：平台级系统架构（Agent Runtime · Workflow · RAG · LLM · 部署）。
- **[software_team_pipeline.md](./software_team_pipeline.md)**：偏 **应用层** Software Team（Coordinator、Artifact、Git、Verification Pipeline）。
- **本文档**：偏 **平台层** Phase 5 Agent + Tool + Task 5.8 `project_runs` Demo。

后续可将 `SoftwareTeamWorkflow.execute_tasks` 与 `SoftwareTeamPipeline` 统一为同一编排入口，并共用 `project_runs/` 格式。

---

## 7. 文件索引（平台层）

```
app/agents/software_team/
├── manager_agent.py
├── product_agent.py
├── architecture_agent.py
├── developer_agent.py
├── reviewer_agent.py
├── tester_agent.py
├── devops_agent.py
├── workflow.py / task.py
├── *_prompt.py / *_tool_manager.py
├── code_change_history.py
├── review_report.py / test_report.py / deployment_report.py
└── tools/
    ├── filesystem_tool.py
    ├── code_tool.py
    ├── terminal_tool.py
    ├── environment_tool.py
    └── terminal_policy.py

applications/software_team/
├── run_*_demo.py
├── run_full_team_demo.py
└── pipeline/
    ├── team_pipeline.py
    ├── run_record.py
    └── demo_clients.py
```
