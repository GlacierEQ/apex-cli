# APEX CLI
## Unified Legal-Ops Terminal | Case 1FDV-23-0001009 | Barton v. [OP]

> **Win condition:** Reunification with Kekoa. Federal escalation (§1983 / RICO) active.

---

## Install

```bash
git clone https://github.com/GlacierEQ/apex-cli
cd apex-cli
npm install
cp .env.example .env   # add GEMINI_API_KEY
```

Get a free Gemini API key: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

## Gemini Commands

```bash
# Interactive REPL (Gemini 2.0 Flash by default)
npm run gemini

# REPL with Gemini Pro (deep reasoning, motion drafting)
npm run gemini:pro

# Daily tactical brief from tactical-plan.json
npm run gemini:daily

# Analyze a file
npm run analyze -- --file hearing.txt --task summarize

# Pipe a document
cat exhibit.txt | npm run analyze -- --task exhibit-review

# Legal research (Gemini Pro)
npm run research -- --query "HRCP 60(b) standard Hawaii Family Court"

# Draft a motion section
npm run draft -- --query "Relief under HRS 571-46 best-interest factors"
```

## REPL Commands

| Command   | Action |
|-----------|--------|
| `/model`  | Toggle flash ↔ pro |
| `/clear`  | Clear conversation history |
| `/status` | Print case status snapshot |
| `/exit`   | Quit |

---

## Multi-Model Router

| Task | Model | Speed |
|------|-------|-------|
| `chat`, `triage`, `summarize`, `analyze`, `exhibit-review` | gemini-2.0-flash | Fast |
| `draft`, `research`, `motion-section`, `federal-memo` | gemini-2.0-pro-exp | Deep |

---

## APEX Ecosystem

- [apex-connector-registry](https://github.com/GlacierEQ/apex-connector-registry) — 15-connector fabric
- [apex-obsidian-vault](https://github.com/GlacierEQ/apex-obsidian-vault) — litigation codex
- [apex-taskade-connector](https://github.com/GlacierEQ/apex-taskade-connector) — task automation

---

## Governing Law Stack

XIV Amend. · §1983 · RICO · *Troxel* · *Santosky* · *Stanley*  
9th Cir: *Wallis* · *Keates* · *Moreland* · *H.J. Inc.*  
HRS §571-46 · §571-46.4 · §92F · HRE 901 · HRCP 60(b) · HPR 9  
HRPC 3.3 · 8.3 · 8.4
