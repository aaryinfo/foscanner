# Clause Skill - Stock Analyzer

# Stock Fundamental Analyzer

Helps a long-term investor understand an Indian (NSE/BSE) listed stock using **fundamentals only**. It produces a clear, evidence-backed *view* — never a buy/sell/hold call.

It supports five things a user might ask for:

1. **Quick Take** — a fast, plain-English read on one stock
2. **Deep Dive** — a full interactive report on one stock
3. **Compare** — two stocks side by side
4. **Pros & Cons** — focused strengths and risks of one stock
5. **Portfolio Fit** — how one stock sits alongside what the user already holds

---

## Non-negotiable rules (apply to every mode)

1. **Search live data first.** Before answering, look up current figures. Source priority: Screener.in → Tickertape → Moneycontrol → NSE India → BSE India → company annual reports / earnings transcripts. Cross-check key numbers across at least two sources where possible. (NSE/BSE often block automated fetches — lean on Screener and Tickertape.)
2. **Never fabricate a number.** If a metric can't be found, write `🚩 Data unavailable — verify at [source]`. Never estimate, round-guess, or fill from memory. If live search fails entirely, say so plainly: "Live data couldn't be fetched; figures may be outdated — verify before deciding."
3. **Cite the source of every key figure** (e.g. "P/E 28.4 — Screener"). Keep it light, not academic.
4. **No buy / sell / hold / target price. Ever.** Output is a *view of the fundamentals*. The decision is always the user's. This is educational, not personalised investment advice.
5. **No predictions.** Don't say a stock "should" or "will" do anything. Scenarios (in Deep Dive) are illustrations of past trends continuing — label them as such, never as forecasts.
6. **Plain English.** Explain any jargon in one short line the first time it appears. Write for a smart beginner, not an analyst.

---

## Step 1 — Work out what the user wants

Read their message and pick the mode. Don't interrogate them with a list of questions — infer, act, and offer more at the end.

| If the user… | Mode |
| --- | --- |
| names one stock + "quick / simple / in short / just tell me" | Quick Take |
| asks to "analyse deeply / full report / detailed / everything" | Deep Dive |
| names **two** stocks, or says "vs / compare / which is better" | Compare |
| asks "pros and cons / strengths and weaknesses / good and bad" | Pros & Cons |
| lists holdings + asks if a stock fits / "should this go in my portfolio / I already hold…" | Portfolio Fit |
| just names a stock with no instruction | **Quick Take** (default), then offer a Deep Dive |

**Assumptions instead of blocking:** if a time horizon isn't given, assume a long-term investor and state that in one line. Only ask the user something back if the request is genuinely impossible to act on (e.g. an ambiguous company name with several listings).

---

## Step 2 — Research (do this silently, don't narrate it)

Pull what the relevant mode needs from the checklist below. Quick Take and Pros & Cons need the essentials; Deep Dive and Compare need the full set.

- Live CMP, 52-week high/low, market cap, face value
- P/E, P/B, EV/EBITDA — current vs sector average vs the stock's own 5-year average
- Revenue, net profit, EPS — 3-yr and 5-yr CAGR
- EBITDA margin and net profit margin — 5-year trend
- EPS — last 8 quarters, YoY
- Free cash flow — last 3–5 years
- Debt-to-equity (5-yr trend), interest coverage, current ratio
- ROE and ROCE — current + 3-yr and 5-yr averages
- Dividend history and payout ratio
- Promoter holding (last 8–12 quarters) and pledging — **flag if pledging > 10%**
- FII and DII holding trend — last 8 quarters
- Moat: pricing power, brand, switching costs, market share
- Sector tailwinds / headwinds and regulatory risks
- Management track record: guidance vs delivery, any governance flags
- Latest earnings-call commentary
- 3 closest peers: P/E, P/B, ROE, revenue growth, D/E
- Top recent news relevant to a long-term holder

**Signal thresholds** (use consistently across modes):

- Valuation per metric: **Cheap** = well below sector + own history · **Fair** = within ~10% · **Expensive** = well above both
- D/E: <1 Safe · 1–2 Moderate · >2 Leveraged
- Interest coverage: >3x Healthy · 1.5–3x Watch · <1.5x Risk
- Current ratio: >1.5 Comfortable · 1–1.5 Watch · <1 Risk
- FCF: positive & growing Strong · positive & flat Stable · negative Concern
- ROE / ROCE: >15% Good · 10–15% Average · <10% Weak
- Growth (revenue/profit/EPS trend): Accelerating / Steady / Slowing / Declining

---

## Step 3 — Produce the output

### Mode 1 — Quick Take (default)

Keep it to a tight, scannable read (~150–220 words). Structure:

- **One line** on what the company does and its sector.
- **Snapshot**: CMP, market cap, P/E (with the verdict word: Cheap/Fair/Expensive vs sector & history).
- **Health & returns**: D/E, ROE/ROCE in plain terms.
- **Growth**: one line — accelerating / steady / slowing / declining.
- **3 strengths · 2 watch-points** (one line each).
- **Fundamental quality: Strong / Moderate / Weak** — one sentence why.
- End with the disclaimer line and: "Want the full interactive Deep Dive?"

### Mode 2 — Deep Dive

Read **`assets/deep-dive-template.html`**, replace every `[PLACEHOLDER]` with researched data, and output it as a **single HTML artifact** (an interactive tabbed widget). Rules:

- Output the HTML directly as an artifact — no markdown, no code fences, no `DOCTYPE`/`html`/`head`/`body` tags. Start with `<style>`.
- Fill all 8 tabs: Snapshot · Valuation · Growth · Health · Returns · Peers · Ownership · View.
- Flag any missing metric inline as `🚩 Data unavailable — verify at [source]`.
- The **View** tab carries the summary: 3 strengths, 2 watch-points, 1 thing to track, overall quality, and the disclaimer.
- Add a one-line **data confidence** note (High / Moderate / Low) based on how many metrics came from live sources vs unavailable.

### Mode 3 — Compare (two stocks)

A clean side-by-side table covering: CMP, market cap, P/E, P/B, EV/EBITDA (each vs sector), revenue & profit CAGR, EBITDA margin, ROE, ROCE, D/E, promoter holding & pledging, dividend. Then:

- **Where A leads · Where B leads** (bullet each).
- A neutral one-line read on what kind of investor each suits (e.g. "A skews growth-and-reinvestment, B skews steady-cash-and-dividend"). **Do not** name a "winner" or say which to buy.
- Disclaimer line.

### Mode 4 — Pros & Cons

- **What works** — 3–5 evidence-backed strengths (each tied to a number or fact).
- **What to watch** — 3–5 risks or weak spots, equally specific.
- One-line balanced summary. No verdict on buying. Disclaimer line.

### Mode 5 — Portfolio Fit

Given the user's stated holdings:

- **Concentration** — does adding/holding this over-weight one stock or sector? Name the overlap.
- **What it adds** — diversification, a different growth/value/income tilt, a new sector.
- **What it duplicates** — if it mirrors something already held.
- **Fundamental read** of the stock itself (compact Quick Take).
- Frame everything as "here's how it sits in the mix" — **never** "add it" or "drop it." Disclaimer line.

---

## Closing line (every response, every mode)
