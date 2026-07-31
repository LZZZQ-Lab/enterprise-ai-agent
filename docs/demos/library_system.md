# 图书管理系统 — 演示指南

演示样例路径：`backend/workspace/library_p0_run13/`

## 生成过程截图

**PRD 自动生成**（ProductAgent 输出 `docs/PRD.md`）：

![PRD 文档示例](docs/images/demo-prd.png)

**流水线运行日志**（多 Agent 协作写入产物）：

![流水线日志](docs/images/demo-pipeline-logs.png)

## 5 分钟演示流程

### 准备

```powershell
# 终端 1：后端
cd backend/workspace/library_p0_run13
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000

# 终端 2：前端（可选）
cd backend/workspace/library_p0_run13/frontend
python -m http.server 5173
```

### Swagger 演示（推荐）

打开 http://localhost:8000/docs ，按顺序操作：

| 步骤 | 接口 | 说明 |
|------|------|------|
| 1 | `GET /api/health` | 系统正常 |
| 2 | `POST /api/books/` | 添加图书 |
| 3 | `POST /api/readers/` | 注册读者 |
| 4 | `POST /api/borrowings/borrow` | 借书 |
| 5 | `GET /api/borrowings/reader/{id}` | 查在借 |
| 6 | `POST /api/borrowings/return` | 还书 |
| 7 | `GET /api/stats/books` | 统计 |

### 示例 JSON

**添加图书**

```json
{
  "title": "三体",
  "author": "刘慈欣",
  "isbn": "9787536692930",
  "category": "科幻",
  "total_stock": 5
}
```

**注册读者**

```json
{
  "name": "张三",
  "id_card": "110101199001011234",
  "phone": "13800138001"
}
```

**借书**（id 按实际返回修改）

```json
{
  "book_id": 1,
  "reader_id": 1
}
```

**还书**

```json
{
  "borrowing_id": 1
}
```

## 演示话术（一句话）

> 输入自然语言需求后，平台约 10 分钟自动生成图书管理系统；Swagger 可现场完成借还书，证明不是 PPT 演示。

## 清空测试数据

```powershell
cd backend/workspace/library_p0_run13
# 先停止后端，再删除数据库
Remove-Item library.db -ErrorAction SilentlyContinue
```

重启后端后会自动重建空库。

## 常见问题

| 现象 | 处理 |
|------|------|
| 前端点击无反应 | 确认后端在 8000 运行；页面 Ctrl+F5 刷新 |
| `/api/items` 404 | 不要用 `http.server` 访问 API，API 只在 8000 |
| 端口占用 | 换 `--port 8001` 并修改 `frontend/app.js` 中 `API_BASE` |
