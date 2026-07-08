import json

md_file = 'july_2026_symbols.md'
html_file = 'monthly_report.html'

with open(md_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

data = []
for i, line in enumerate(lines):
    line = line.strip()
    if not line or line.startswith('|---'): continue
    parts = [p.strip() for p in line.split('|')[1:-1]]
    if i > 0 and len(parts) == 4:
        symbol = parts[0]
        market = "NSE" if symbol.endswith(".NS") or symbol.endswith(".BO") else "GLOBAL"
        data.append({
            "symbol": symbol,
            "market": market,
            "from_date": parts[1],
            "to_date": parts[2],
            "trend": parts[3]
        })

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Monthly Reversal List — Gann AI</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
/* ── Reset & Base ─────────────────────────────────────────── */
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:       #0B0F1A;
  --bg2:      #111827;
  --bg3:      #1A2236;
  --border:   #1E2D45;
  --gold:     #C9A84C;
  --gold-dim: #8A6E2F;
  --cyan:     #00D4FF;
  --green:    #00C896;
  --red:      #FF3B5C;
  --text:     #D0DBF0;
  --muted:    #5A6A88;
  --mono:     'Share Tech Mono', monospace;
  --sans:     'Inter', sans-serif;
}}
body{{background-color:var(--bg);color:var(--text);font-family:var(--sans);height:100vh;display:flex;flex-direction:column;}}

/* ── Custom Scrollbars ────────────────────────────────────── */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: rgba(201, 168, 76, 0.3); border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(201, 168, 76, 0.7); }}

/* ── Topbar ───────────────────────────────────────────────── */
.topbar{{background:rgba(17, 24, 39, 0.95);backdrop-filter:blur(12px);border-bottom:1px solid rgba(30, 45, 69, 0.8);
  display:flex;align-items:center;padding:0 24px;height:60px;gap:20px;z-index:10;box-shadow:0 4px 20px rgba(0,0,0,0.5);}}
.logo{{font-family:var(--mono);font-size:16px;color:var(--gold);letter-spacing:2px;white-space:nowrap;text-decoration:none;}}
.logo span{{color:var(--muted)}}
.topbar-info{{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted);display:flex;gap:24px;align-items:center;}}
.btn-nav{{color:var(--text);text-decoration:none;font-size:12px;padding:6px 12px;background:var(--bg3);border-radius:4px;border:1px solid var(--border);transition:all 0.2s;font-family:var(--mono);}}
.btn-nav:hover{{border-color:var(--gold);color:var(--gold);}}

/* ── Main Layout ──────────────────────────────────────────── */
.container{{flex:1;padding:24px;max-width:1200px;margin:0 auto;width:100%;display:flex;flex-direction:column;gap:20px;overflow-y:auto;}}

/* ── Header & Metrics ─────────────────────────────────────── */
.header{{display:flex;justify-content:space-between;align-items:flex-end;}}
.page-title{{font-size:24px;font-weight:600;letter-spacing:1px;margin-bottom:8px;}}
.page-subtitle{{font-family:var(--mono);color:var(--muted);font-size:13px;}}

/* ── Controls (Filters & Export) ──────────────────────────── */
.controls{{display:flex;gap:16px;background:var(--bg2);padding:16px;border-radius:8px;border:1px solid var(--border);align-items:center;flex-wrap:wrap;}}
.control-group{{display:flex;flex-direction:column;gap:6px;}}
.control-group label{{font-size:11px;color:var(--muted);font-family:var(--mono);text-transform:uppercase;}}
.control-group select, .control-group input{{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:4px;font-family:var(--sans);font-size:13px;outline:none;min-width:150px;}}
.control-group select:focus, .control-group input:focus{{border-color:var(--gold);}}
.btn-export{{background:var(--gold);color:#000;border:none;padding:10px 20px;font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;border-radius:4px;cursor:pointer;transition:all 0.2s;margin-left:auto;display:flex;align-items:center;gap:8px;}}
.btn-export:hover{{background:#E8C060;box-shadow:0 0 15px rgba(201,168,76,0.4);transform:translateY(-1px);}}

/* ── Table ────────────────────────────────────────────────── */
.table-wrapper{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;overflow-x:auto;box-shadow:0 10px 30px rgba(0,0,0,0.3);}}
table{{width:100%;border-collapse:collapse;text-align:left;font-family:var(--sans);font-size:13px;}}
th{{background:var(--bg3);padding:14px 16px;font-family:var(--mono);font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;position:sticky;top:0;}}
td{{padding:12px 16px;border-bottom:1px solid rgba(30, 45, 69, 0.4);vertical-align:middle;}}
tr{{transition:background 0.2s;}}
tr:hover{{background:rgba(255,255,255,0.02);}}

.badge{{padding:4px 8px;border-radius:4px;font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:1px;}}
.badge-bull{{background:rgba(0, 200, 150, 0.1);color:var(--green);border:1px solid rgba(0, 200, 150, 0.2);}}
.badge-bear{{background:rgba(255, 59, 92, 0.1);color:var(--red);border:1px solid rgba(255, 59, 92, 0.2);}}

.empty-state{{text-align:center;padding:40px;color:var(--muted);font-style:italic;}}
</style>
</head>
<body>

<div class="topbar">
  <a href="/" class="logo">ANTIGRAVITY <span>/ SCANNER</span></a>
  <div class="topbar-info">
    <a href="/" class="btn-nav">← Back to Dashboard</a>
  </div>
</div>

<div class="container">
  <div class="header">
    <div>
      <h1 class="page-title">Monthly Reversal Confluence List</h1>
      <div class="page-subtitle">Based on Gann Time Cycles</div>
    </div>
  </div>

  <div class="controls">
    <div class="control-group">
      <label>Market</label>
      <select id="filterMarket" onchange="applyFilters()">
        <option value="ALL">All Markets</option>
        <option value="NSE">NSE F&O</option>
        <option value="GLOBAL">Global Assets</option>
      </select>
    </div>
    <div class="control-group">
      <label>Trend</label>
      <select id="filterTrend" onchange="applyFilters()">
        <option value="ALL">All Trends</option>
        <option value="BULL REVERSAL">Bull Reversal</option>
        <option value="BEAR REVERSAL">Bear Reversal</option>
      </select>
    </div>
    <div class="control-group">
      <label>Search Symbol</label>
      <input type="text" id="searchBox" placeholder="e.g. SWIGGY" onkeyup="applyFilters()"/>
    </div>
    <button class="btn-export" onclick="exportCSV()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
      Export CSV
    </button>
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Market</th>
          <th>From Date</th>
          <th>To Date</th>
          <th>Trend</th>
        </tr>
      </thead>
      <tbody id="tableBody">
      </tbody>
    </table>
  </div>
</div>

<script>
const globalData = {json.dumps(data)};

function renderTable() {{
  const tbody = document.getElementById('tableBody');
  const marketFilter = document.getElementById('filterMarket').value;
  const trendFilter = document.getElementById('filterTrend').value;
  const search = document.getElementById('searchBox').value.toLowerCase();

  let filtered = globalData.filter(item => {{
    if(marketFilter !== 'ALL' && item.market !== marketFilter) return false;
    if(trendFilter !== 'ALL' && item.trend !== trendFilter) return false;
    if(search && !item.symbol.toLowerCase().includes(search)) return false;
    return true;
  }});

  if(filtered.length === 0) {{
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No matching records found.</td></tr>`;
    return;
  }}

  let html = '';
  filtered.forEach(row => {{
    const isBull = row.trend.includes('BULL');
    const badgeCls = isBull ? 'badge-bull' : 'badge-bear';
    
    html += `
      <tr>
        <td style="font-weight:600">${{row.symbol}}</td>
        <td style="color:var(--muted);font-size:11px;">${{row.market}}</td>
        <td style="font-family:var(--mono)">${{row.from_date}}</td>
        <td style="font-family:var(--mono)">${{row.to_date}}</td>
        <td><span class="badge ${{badgeCls}}">${{row.trend}}</span></td>
      </tr>
    `;
  }});

  tbody.innerHTML = html;
}}

function applyFilters() {{
  renderTable();
}}

function exportCSV() {{
  const table = document.querySelector("table");
  const rows = table.querySelectorAll("tr");
  let csv = [];
  
  for (let i = 0; i < rows.length; i++) {{
    let row = [], cols = rows[i].querySelectorAll("td, th");
    if(cols.length === 1 && cols[0].classList.contains('empty-state')) continue; 
    
    for (let j = 0; j < cols.length; j++) {{
      let data = cols[j].innerText.replace(/(\\r\\n|\\n|\\r)/gm, " ");
      data = data.replace(/"/g, '""');
      row.push('"' + data + '"');
    }}
    csv.push(row.join(","));
  }}

  const csvString = csv.join("\\n");
  const blob = new Blob([csvString], {{ type: "text/csv;charset=utf-8;" }});
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", `Monthly_Report.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}}

renderTable();
</script>
</body>
</html>'''

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)
