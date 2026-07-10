with open('gann_dashboard.html', 'r', encoding='utf-8') as f:
    code = f.read()

target = """      if (results.length === 0) {
        tableBody.innerHTML = '';
        emptyMsg.classList.remove('hidden');
      } else {
        tableBody.innerHTML = results.map(r => {"""

replace = """      const screenerTopPicks = results.filter(r => r.confluence_match !== false);
      if (screenerTopPicks.length === 0) {
        tableBody.innerHTML = '';
        emptyMsg.classList.remove('hidden');
      } else {
        tableBody.innerHTML = screenerTopPicks.map(r => {"""

if target in code:
    code = code.replace(target, replace)
    with open('gann_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Patched gann_dashboard.html successfully")
else:
    print("Target not found in gann_dashboard.html")
