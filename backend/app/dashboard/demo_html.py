"""Dashboard Demo 单页（内联 HTML，免静态资源部署）。"""

DEMO_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Infra Dashboard Demo</title>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a2332;
      --border: #2d3a4f;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3d9cf0;
      --ok: #3dd68c;
      --warn: #f5a524;
      --err: #f04438;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }
    header {
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      justify-content: space-between;
    }
    h1 { margin: 0; font-size: 1.25rem; font-weight: 600; }
    .meta { color: var(--muted); font-size: 0.85rem; }
    main { padding: 1.25rem 1.5rem 2rem; max-width: 1400px; margin: 0 auto; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }
    .kpi {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.85rem 1rem;
    }
    .kpi label { display: block; font-size: 0.75rem; color: var(--muted); }
    .kpi strong { font-size: 1.35rem; font-variant-numeric: tabular-nums; }
    section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
    }
    section h2 {
      margin: 0 0 0.75rem;
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--accent);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }
    th, td {
      text-align: left;
      padding: 0.45rem 0.5rem;
      border-bottom: 1px solid var(--border);
    }
    th { color: var(--muted); font-weight: 500; }
    .badge {
      display: inline-block;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-size: 0.75rem;
      background: #243044;
    }
    .badge.active { color: var(--ok); }
    .badge.idle { color: var(--muted); }
    .err-banner {
      background: #3a1f1f;
      border: 1px solid var(--err);
      color: #ffb4ae;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      display: none;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
    pre {
      margin: 0;
      font-size: 0.78rem;
      overflow: auto;
      max-height: 220px;
      color: var(--muted);
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>AI Infra Dashboard Demo</h1>
      <div class="meta">Enterprise AI Platform · Phase 7.8</div>
    </div>
    <div class="meta" id="refresh-meta">加载中…</div>
  </header>
  <main>
    <div class="err-banner" id="err"></div>
    <div class="kpis" id="kpis"></div>
    <section>
      <h2>模型运行状态</h2>
      <table>
        <thead>
          <tr>
            <th>注册名</th>
            <th>Model ID</th>
            <th>Provider</th>
            <th>状态</th>
            <th>QPS*</th>
            <th>Latency (ms)</th>
            <th>Tokens (P/C)</th>
            <th>请求数</th>
          </tr>
        </thead>
        <tbody id="models"></tbody>
      </table>
      <p class="meta" style="margin:0.5rem 0 0">* 模型 QPS 为基于平均延迟的估算值；全局 QPS 见上方 KPI。</p>
    </section>
    <div class="grid-2">
      <section>
        <h2>GPU</h2>
        <table>
          <thead>
            <tr><th>Index</th><th>Util %</th><th>显存 (MiB)</th><th>温度 °C</th></tr>
          </thead>
          <tbody id="gpu"></tbody>
        </table>
      </section>
      <section>
        <h2>缓存命中率</h2>
        <table>
          <thead>
            <tr><th>Layer</th><th>Hits</th><th>Misses</th><th>Hit Rate</th></tr>
          </thead>
          <tbody id="cache"></tbody>
        </table>
      </section>
    </div>
    <div class="grid-2">
      <section>
        <h2>Agent 运行情况</h2>
        <pre id="agents"></pre>
      </section>
      <section>
        <h2>服务发现</h2>
        <pre id="discovery"></pre>
      </section>
    </div>
  </main>
  <script>
    const OVERVIEW_URL = "/api/v1/infra/dashboard/overview";
    const POLL_MS = 5000;

    function fmt(n, digits = 2) {
      if (n == null || Number.isNaN(n)) return "—";
      return typeof n === "number" ? n.toFixed(digits) : String(n);
    }

    function pct(rate) {
      if (rate == null) return "—";
      return (Number(rate) * 100).toFixed(1) + "%";
    }

    function render(data) {
      const k = document.getElementById("kpis");
      const tokens = data.gateway_tokens || {};
      k.innerHTML = [
        ["HTTP QPS (est.)", fmt(data.http_qps_estimate)],
        ["Latency avg (ms)", fmt(data.http_latency_avg_ms, 1)],
        ["错误率", pct(data.http_error_rate)],
        ["HTTP 请求", data.http_requests_total ?? 0],
        ["Gateway Tokens", tokens.total_tokens ?? 0],
        ["Gateway 请求", tokens.total_requests ?? 0],
      ].map(([label, val]) =>
        `<div class="kpi"><label>${label}</label><strong>${val}</strong></div>`
      ).join("");

      const models = data.models || [];
      document.getElementById("models").innerHTML = models.length
        ? models.map(m => `<tr>
            <td>${m.registry_name}</td>
            <td>${m.model_id}</td>
            <td>${m.provider}</td>
            <td><span class="badge ${m.status}">${m.status}</span></td>
            <td>${fmt(m.qps)}</td>
            <td>${fmt(m.latency_avg_ms, 1)}</td>
            <td>${m.tokens_prompt}/${m.tokens_completion}</td>
            <td>${m.requests_total}</td>
          </tr>`).join("")
        : `<tr><td colspan="8" class="meta">暂无注册模型或尚无请求</td></tr>`;

      const gpu = data.gpu || [];
      document.getElementById("gpu").innerHTML = gpu.length
        ? gpu.map(g => `<tr>
            <td>${g.index}</td>
            <td>${fmt(g.utilization_percent, 0)}</td>
            <td>${fmt(g.memory_used_mib, 0)} / ${fmt(g.memory_total_mib, 0)}</td>
            <td>${fmt(g.temperature_c, 0)}</td>
          </tr>`).join("")
        : `<tr><td colspan="4" class="meta">无 GPU 指标（nvidia-smi 未可用或未采集）</td></tr>`;

      const layers = (data.cache && data.cache.layers) || {};
      const cacheKeys = Object.keys(layers);
      document.getElementById("cache").innerHTML = cacheKeys.length
        ? cacheKeys.map(key => {
            const L = layers[key];
            return `<tr><td>${key}</td><td>${L.hits}</td><td>${L.misses}</td><td>${pct(L.hit_rate)}</td></tr>`;
          }).join("")
        : `<tr><td colspan="4" class="meta">backend: ${(data.cache && data.cache.backend) || "memory"} · 尚无缓存访问</td></tr>`;

      document.getElementById("agents").textContent = JSON.stringify(data.agents || {}, null, 2);
      document.getElementById("discovery").textContent = JSON.stringify(data.service_discovery || {}, null, 2);

      document.getElementById("refresh-meta").textContent =
        "上次更新: " + (data.generated_at || new Date().toISOString()) + " · 每 " + (POLL_MS/1000) + "s 刷新";
    }

    async function load() {
      const err = document.getElementById("err");
      try {
        const res = await fetch(OVERVIEW_URL);
        if (!res.ok) throw new Error(res.status + " " + res.statusText);
        render(await res.json());
        err.style.display = "none";
      } catch (e) {
        err.textContent = "无法加载 " + OVERVIEW_URL + ": " + e.message;
        err.style.display = "block";
      }
    }

    load();
    setInterval(load, POLL_MS);
  </script>
</body>
</html>
"""
