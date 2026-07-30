# vLLM 推理服务部署指南

> Task 2.4：将 Qwen2.5-Instruct 部署为生产级 OpenAI Compatible API 服务。

本文档说明如何在 GPU 服务器上部署 vLLM，并通过 `/v1/chat/completions` 提供推理能力。

**注意：** 本 Task **不修改 Agent 代码**。Platform 可通过现有 `OpenAIProvider` + `OPENAI_BASE_URL` 对接 vLLM 服务。

---

## 架构概览

```
Agent / ChatAgent
    ↓
OpenAIProvider.chat()
    ↓
HTTP POST /v1/chat/completions
    ↓
vLLM OpenAI API Server
    ↓
Qwen2.5-Instruct (GPU)
```

---

## 1. 安装方式

### 1.1 推荐环境

| 项目 | 要求 |
|------|------|
| **操作系统** | Linux（Ubuntu 22.04+）或 **WSL2** |
| **Python** | 3.10 / 3.11 |
| **CUDA** | 12.x（与 PyTorch、驱动匹配） |
| **GPU 显存** | ≥ 4 GB（0.5B）；≥ 8 GB（1.5B）；≥ 16 GB（7B AWQ） |

> 官方 vLLM **主要支持 Linux**。Windows 原生建议使用 **WSL2**，或参考文末 FAQ 中的社区 Windows 构建。

### 1.2 Linux / WSL2 安装

```bash
cd backend

# 1) 安装 PyTorch（CUDA 12.x）
pip install torch --index-url https://download.pytorch.org/whl/cu124

# 2) 安装 vLLM
pip install -r requirements-vllm.txt

# 3) 验证
python scripts/check_vllm_service.py
vllm --version
```

### 1.3 Windows（WSL2）安装

```powershell
# 在 PowerShell 中进入 WSL
wsl

# 在 Ubuntu 内执行 1.2 的步骤
cd /mnt/d/path/to/enterprise-ai-agent/backend
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements-vllm.txt
```

### 1.4 依赖文件

- `backend/requirements-vllm.txt` — vLLM + httpx（API 验证）

---

## 2. 启动命令

### 2.1 默认模型（4GB 显存友好）

推荐使用 **`Qwen/Qwen2.5-0.5B-Instruct`**（约 1GB 显存，适合 RTX 2050 4GB）：

```bash
cd backend
bash scripts/start_vllm_server.sh
```

等价手动命令：

```bash
vllm serve Qwen/Qwen2.5-0.5B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 2048 \
  --gpu-memory-utilization 0.85 \
  --enforce-eager \
  --dtype auto \
  --trust-remote-code
```

### 2.2 较大模型（需更多显存）

| 模型 | 建议显存 | 命令示例 |
|------|----------|----------|
| `Qwen/Qwen2.5-1.5B-Instruct` | ≥ 6 GB | `VLLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct bash scripts/start_vllm_server.sh` |
| `Qwen/Qwen2.5-7B-Instruct-AWQ` | ≥ 16 GB | 需量化权重 + 调低 `--gpu-memory-utilization` |

### 2.3 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VLLM_MODEL` | `Qwen/Qwen2.5-0.5B-Instruct` | HuggingFace 模型 ID |
| `VLLM_HOST` | `0.0.0.0` | 监听地址 |
| `VLLM_PORT` | `8000` | 服务端口 |
| `VLLM_MAX_LEN` | `512` | 最大上下文（4GB 显存默认） |
| `VLLM_GPU_UTIL` | `0.70` | GPU 显存占用比例（4GB 建议 ≤0.75） |
| `VLLM_PROFILE` | `baseline` | Task 4.4：`baseline` / `optimized`（见 `data/vllm_profiles.json`） |

### 2.4 Windows 启动（WSL2）

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts/start_vllm_server.ps1
```

---

## 3. API 调用方式

### 3.1 健康检查

```bash
curl http://127.0.0.1:8000/v1/models
```

### 3.2 Chat Completions

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }'
```

### 3.3 项目内置验证脚本

```bash
cd backend
python scripts/test_vllm_api.py
python scripts/test_vllm_api.py --prompt "你好，请介绍一下自己"
```

### 3.4 对接 Platform（不修改 Agent）

在 `backend/.env` 中配置 OpenAI 兼容端点指向 vLLM：

```env
MODEL_PROVIDER=openai
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct
API_KEY=EMPTY
```

Agent 仍通过 `get_llm_client()` → `OpenAIProvider` 调用，无需改代码。

---

## 4. GPU 要求

### 4.1 当前开发机（参考）

| 项目 | 值 |
|------|-----|
| GPU | NVIDIA GeForce RTX 2050 |
| 显存 | 4 GB |
| 驱动 CUDA | 12.8 |

### 4.2 模型与显存建议

| 模型 | FP16 显存（约） | 4GB GPU | 8GB GPU |
|------|----------------|---------|---------|
| Qwen2.5-0.5B-Instruct | ~1.2 GB | ✅ 推荐 | ✅ |
| Qwen2.5-1.5B-Instruct | ~3.5 GB | ⚠️ 需 `--gpu-memory-utilization 0.9` | ✅ |
| Qwen2.5-7B-Instruct | ~14 GB | ❌ | ❌（需 AWQ + 更大显存） |

### 4.3 调优参数

显存不足时可尝试（启动脚本已默认 `512` / `0.70` / `--swap-space 2`）：

```bash
export VLLM_MAX_LEN=512
export VLLM_GPU_UTIL=0.65
bash scripts/start_vllm_server.sh
```

离线本地权重时另设 `HF_HUB_OFFLINE=1` 与 `VLLM_MODEL=/path/to/snapshot`。

---

## 5. 常见问题

### Q1: Windows 下 `pip install vllm` 失败？

**A:** 官方 vLLM 面向 Linux。请使用 **WSL2 + Ubuntu**，或在 Linux GPU 服务器部署。Windows 社区构建可参考 [aivrar/vllm-windows-build](https://github.com/aivrar/vllm-windows-build)（非官方）。

### Q2: `CUDA out of memory` 或 `Free memory on device ... less than desired GPU memory utilization`？

**A:** vLLM 启动时会按 `gpu_memory_utilization × 总显存` 预留 KV 等空间。若 **当前空闲显存** 小于该值（常见于 4GB 卡上仍有桌面/浏览器占显存），Engine 会直接失败。

- 换更小模型（0.5B）
- **降低** `VLLM_GPU_UTIL`（如 `0.65`～`0.70`），不要提高到 0.9
- 降低 `VLLM_MAX_LEN`（512 或 1024）
- WSL 内执行 `nvidia-smi`，关闭其它占 GPU 的进程
- 使用 `scripts/start_vllm_server.sh` 默认参数后重试

### Q3: 首次启动很慢？

**A:** HuggingFace 会下载模型权重（约 1GB+）。WSL 推荐镜像 + 项目脚本：

```bash
cd backend
source .venv-vllm/bin/activate
export HF_ENDPOINT=https://hf-mirror.com
unset HF_HUB_OFFLINE
bash scripts/download_vllm_model.sh
bash scripts/verify_vllm_model.sh
```

### Q3b: `Cannot find any model weights with .../snapshots/...`？

**A:** snapshot 里只有 `config.json`、分词器，**没有** `model.safetensors`（下载中断或未拉权重）。在 WSL 执行：

```bash
unset HF_HUB_OFFLINE
export HF_ENDPOINT=https://hf-mirror.com
bash scripts/download_vllm_model.sh
```

确认 `verify_vllm_model.sh` 输出 `OK: found ... weight file(s)` 后再 `export HF_HUB_OFFLINE=1` 离线启动（可选）。

### Q3d: `ss` 显示 8000 在 LISTEN，但 `curl 127.0.0.1:8000` 立刻 (7) 失败？

**A:** 常见于 `%USERPROFILE%\.wslconfig` 里 **`networkingMode=mirrored`** 且 **`firewall=true`** 时，WSL 内访问 **127.0.0.1** 会走错网络栈（Microsoft 已知问题），服务其实在跑，只是本机回环地址连不上。

**立刻可用的测法（在 WSL）：**

```bash
bash scripts/probe_vllm_localhost.sh
# 或
curl -m 10 "http://$(hostname -I | awk '{print $1}'):8000/health"
curl -m 10 "http://$(hostname -I | awk '{print $1}'):8000/v1/models"
```

若 `probe` 里 **LAN IP 为 HTTP 200、127.0.0.1 失败**，即属此情况。Platform 在 **同一 WSL** 里跑时，`.env` 可设：

```env
VLLM_ENDPOINT=http://<上面 probe 显示的 IP>:8000/v1
```

**从 Windows 本机访问 vLLM** 仍要用 `127.0.0.1:8000` 时，可尝试修正 WSL 网络（改完后 **PowerShell** 执行 `wsl --shutdown` 再开 WSL）：

```ini
[wsl2]
networkingMode=mirrored
hostAddressLoopback=true
firewall=false
```

或开发阶段暂时 **去掉** `networkingMode=mirrored`（恢复默认 NAT，WSL 内 `127.0.0.1` 通常正常）。也可保留 mirrored，仅把 `firewall=false` 或配置 Hyper-V 防火墙放行 8000。

### Q3c: `Could not find nvcc` / FlashInfer JIT 失败？

**A:** vLLM V1 默认用 FlashInfer 做 top-k/top-p 采样，首次会 JIT 编译，需要 WSL 内安装 **CUDA Toolkit**（含 `nvcc`）。多数 WSL 开发机只有 Windows 显卡驱动、没有 Toolkit。

`scripts/start_vllm_server.sh` 在检测不到 `nvcc` 时会自动设置：

```bash
export VLLM_USE_FLASHINFER_SAMPLER=0
```

改回 PyTorch 采样即可启动（略慢，功能正常）。若已安装 Toolkit，可 `export VLLM_USE_FLASHINFER_SAMPLER=1` 启用 FlashInfer。

### Q4: `/v1/chat/completions` 连接被拒绝？

**A:**
1. 确认 vLLM 已启动：`python scripts/check_vllm_service.py`
2. 检查端口：`curl http://127.0.0.1:8000/v1/models`
3. WSL2 下从 Windows 访问使用 `http://127.0.0.1:8000`（WSL 端口转发）

### Q4b: WSL 运行 `start_vllm_server.sh` 报 `$'\r': command not found`？

**A:** 脚本被存成 **Windows 换行（CRLF）**。在 WSL 的 `backend` 目录执行：

```bash
sed -i 's/\r$//' scripts/*.sh
# 或
python3 scripts/fix_sh_crlf.py
bash scripts/start_vllm_server.sh
```

仓库已添加 `.gitattributes` 固定 `*.sh` 为 LF；若仍出现，可在 VS Code/Cursor 右下角把该文件改为 **LF** 再保存。

### Q5: 与 Task 2.2 `LocalProvider` 的区别？

| 方式 | 特点 |
|------|------|
| **LocalProvider** | 进程内 Transformers 推理，适合开发调试 |
| **vLLM 服务** | 独立 HTTP 服务，高并发、生产级、OpenAI 兼容 |

生产环境推荐 vLLM；开发机可选用 LocalProvider。

### Q6: 如何查看服务状态？

```bash
cd backend
python scripts/check_vllm_service.py
```

### Q7: Platform 如何对接 vLLM（Task 2.5）？

1. 启动 vLLM 服务（见上文）
2. 配置 `backend/.env`：

```env
MODEL_PROVIDER=vllm
VLLM_ENDPOINT=http://127.0.0.1:8000/v1
VLLM_API_KEY=EMPTY
MODEL_NAME=Qwen2.5
```

3. 验证对接：

```bash
# 离线（Mock Client，无需 vLLM 进程）
python scripts/test_vllm_integration.py --mock-client

# 在线（需 vLLM 已启动）
python scripts/test_vllm_integration.py --live
```

Agent 通过 `get_llm_client()` → `VLLMProvider` 调用，**无需修改 Agent Runtime**。

### Q8: 启动报错 `NVIDIA driver ... too old (found version 12080)`？

**原因：** 若 pip 安装了 **vLLM 0.25+**，会自动拉 **torch 2.11+cu130**，需要 **CUDA 13 级别驱动**；而 WSL 常见为 **572.xx / CUDA 12.8**（驱动版本 12080），不兼容。

**方案 A（推荐，驱动可升级时）：** 在 Windows 安装最新 [GeForce 驱动](https://www.nvidia.com/Download/index.aspx)，重启后再 `bash scripts/start_vllm_server.sh`。

**方案 B（保持当前驱动）：** 降级为 **torch 2.6 cu124 + vLLM 0.10.x**：

```bash
cd backend
bash scripts/fix_vllm_cu124.sh
```

网络不稳定时多跑几次；成功后用 `bash scripts/verify_vllm_env.sh` 确认 `cuda True` 且能打印 GPU 名称。

---

## 相关脚本

| 脚本 | 说明 |
|------|------|
| `scripts/start_vllm_server.sh` | Linux/WSL 启动服务 |
| `scripts/start_vllm_server.ps1` | Windows 调 WSL 启动 |
| `scripts/test_vllm_api.py` | 验证 `/v1/chat/completions` |
| `scripts/check_vllm_service.py` | 检查依赖与服务状态 |

---

## 参考链接

- [vLLM 官方文档](https://docs.vllm.ai/)
- [vLLM Quickstart](https://docs.vllm.ai/en/stable/getting_started/quickstart/)
- [Qwen2.5 HuggingFace](https://huggingface.co/Qwen)
