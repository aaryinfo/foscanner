md_file = 'july_2026_symbols.md'
html_file = 'monthly_report.html'

with open(md_file, 'r') as f:
    lines = f.readlines()

html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Monthly Symbol List</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<style>
body { background-color: #0B0F1A; color: #D0DBF0; font-family: 'Inter', sans-serif; padding: 20px; }
table { border-collapse: collapse; width: 100%; max-width: 800px; margin: 0 auto; background: rgba(17, 24, 39, 0.75); }
th, td { border: 1px solid rgba(30, 45, 69, 0.5); padding: 10px; text-align: left; }
th { color: #C9A84C; font-family: 'Share Tech Mono', monospace; text-transform: uppercase; letter-spacing: 2px; }
td { font-family: 'Share Tech Mono', monospace; font-size: 14px; }
h1 { color: #C9A84C; font-family: 'Share Tech Mono', monospace; text-align: center; letter-spacing: 3px; }
.bull { color: #00C896; }
.bear { color: #FF3B5C; }
</style>
</head>
<body>
<h1>Monthly Reversal Confluence List</h1>
<table>
'''

for i, line in enumerate(lines):
    line = line.strip()
    if not line or line.startswith('|---'): continue
    parts = [p.strip() for p in line.split('|')[1:-1]]
    if i == 0:
        html += '<tr>' + ''.join(f'<th>{p}</th>' for p in parts) + '</tr>\\n'
    else:
        html += '<tr>'
        for j, p in enumerate(parts):
            if j == 3: # Trend
                if 'BULL' in p:
                    html += f'<td class="bull">{p}</td>'
                elif 'BEAR' in p:
                    html += f'<td class="bear">{p}</td>'
                else:
                    html += f'<td>{p}</td>'
            else:
                html += f'<td>{p}</td>'
        html += '</tr>\\n'

html += '''</table>
</body>
</html>'''

with open(html_file, 'w') as f:
    f.write(html)
