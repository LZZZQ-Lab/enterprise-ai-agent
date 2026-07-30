# Task 7.7 Kubernetes 部署

企业级 K8s 清单：**API**、**vLLM**、**Redis**、**Chroma（VectorDB）**、**Ingress**、**ConfigMap/Secret**、**HPA 自动扩缩容**。

## 目录结构

```text
infra/k8s/
  namespace.yaml
  configmap.yaml
  secret.example.yaml    # 复制为 secret.yaml 后 apply（勿提交密钥）
  redis.yaml             # Redis + PVC + Service
  chroma.yaml            # VectorDB + PVC + Service
  vllm.yaml              # GPU 推理 + PVC (HF cache) + Service
  api.yaml               # API + Agent Worker + PVC + Service
  ingress.yaml           # 对外入口（需集群 Ingress Controller）
  hpa.yaml               # API / vLLM 水平扩缩容
  kustomization.yaml
```

## 前置条件

- Kubernetes 1.26+
- **NVIDIA Device Plugin**（vLLM 申请 `nvidia.com/gpu`）
- **Metrics Server**（HPA 依赖）
- **Ingress NGINX**（或修改 `ingressClassName`）
- 默认 StorageClass（PVC 动态供给）

验证 GPU 节点：

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```

## 构建并推送 API 镜像

在仓库根目录：

```bash
docker build -f deploy/Dockerfile -t enterprise-ai-agent/api:latest .
# docker tag ... && docker push ...   # 推送到企业镜像仓库后改 kustomization images
```

## 部署步骤

```bash
cd deploy/k8s
cp secret.example.yaml secret.yaml
# 编辑 secret.yaml 填入 API_KEY / VLLM_API_KEY

kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f redis.yaml
kubectl apply -f chroma.yaml
kubectl apply -f vllm.yaml
kubectl apply -f api.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
```

或使用 Kustomize（会一并 apply `secret.example.yaml`，生产请改用外部 Secret 管理）：

```bash
kubectl apply -k deploy/k8s
```

## 访问

| 方式 | 地址 |
|------|------|
| Ingress | http://enterprise-ai.local（hosts 指向 Ingress IP） |
| 端口转发 | `kubectl -n enterprise-ai port-forward svc/api 8001:8001` |

- 健康检查：`/health`
- Swagger：`/docs`
- 指标：`/metrics`

## 自动扩缩容（HPA）

| 工作负载 | min | max | 指标 |
|----------|-----|-----|------|
| **api** | 2 | 10 | CPU 70%、内存 80% |
| **vllm** | 1 | 4 | 内存 75%（每 Pod 1 GPU） |

> vLLM 扩缩容需集群具备足够 **GPU 配额**；多副本时建议配合 Task 7.5 `VLLM_NODES` 或服务发现注册多个 vLLM Service Endpoint。

## 与 Phase 7 能力对齐

| 能力 | K8s 配置 |
|------|----------|
| Inference Gateway | `ENABLE_INFERENCE_GATEWAY=true` |
| Service Discovery | `VLLM_NODES` 指向集群内 `vllm:8000` |
| Model Cache (Redis) | `CACHE_BACKEND=redis`、`REDIS_URL` |
| Vector RAG | `CHROMA_HOST=chroma` |
| 监控 | `ENABLE_INFRA_METRICS=true`，Prometheus 刮取 `/metrics` |

## 生产建议

1. 将 `secret.yaml` 纳入 Sealed Secrets / 云 KMS，勿提交 Git。
2. API 使用 **ReadWriteMany** 共享卷或对象存储承载 `knowledge_uploads`（当前为 RWO 单副本写）。
3. vLLM 大模型可拆独立节点池 + `nodeSelector` / `tolerations`（可按需追加到 `vllm.yaml`）。
4. 对接 **Prometheus + Grafana** 与 Phase 7.8 Dashboard。

Compose 对照见 [../README.md](../README.md) 与 [../../docs/production_deploy.md](../../docs/production_deploy.md)。
