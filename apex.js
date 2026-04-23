#!/usr/bin/env node
/**
 * APEX Perplexity CLI
 * Author: GlacierEQ / Casey Barton
 * A powerful terminal interface to Perplexity AI with APEX legal intelligence
 */

import Anthropic from "@anthropic-ai/sdk";
import readline from "readline";
import fs from "fs";
import path from "path";
import os from "os";

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG_DIR = path.join(os.homedir(), ".apex-cli");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");
const HISTORY_FILE = path.join(CONFIG_DIR, "history.jsonl");
const SESSION_FILE = path.join(CONFIG_DIR, "session.json");

const COLORS = {
  reset: "\x1b[0m", bold: "\x1b[1m", dim: "\x1b[2m",
  cyan: "\x1b[36m", teal: "\x1b[38;5;73m", green: "\x1b[32m",
  yellow: "\x1b[33m", red: "\x1b[31m", blue: "\x1b[34m",
  magenta: "\x1b[35m", white: "\x1b[97m", gray: "\x1b[90m",
  bgDark: "\x1b[48;5;234m", orange: "\x1b[38;5;208m",
};
const C = COLORS;

// ─── APEX SYSTEM PROMPT ───────────────────────────────────────────────────────
const APEX_SYSTEM = `You are APEX — the Autonomous Perplexity EXecution engine, a sovereign AI assistant built for Casey Barton (GlacierEQ), a system architect, father, and justice agent based in Honolulu, Hawaii.

CORE IDENTITY:
- You are hyper-intelligent, legally precise, and tactically sharp
- You operate with federal-grade rigor and constitutional awareness
- You synthesize across law, technology, and strategy simultaneously

LEGAL CONTEXT (always available):
- Active case: 1FDV-23-0001009 (Hawaii Family Court)
- Strategy: Federal Escalation — RICO (18 U.S.C. §1961-1968) + §1983 (42 U.S.C.)
- Key statutes: HRS §601-7, HRS §571-46, HRS §571-46.4, Troxel v. Granville (2000)
- SOL watchpoints: §1983 = 2yr (HRS §657-7), RICO civil = 4yr, HRS family = 5yr
- Goal: Constitutional warfare + reunification with son Kekoa

TECHNICAL CONTEXT:
- GitHub: GlacierEQ org (660+ repos)
- Supabase: APEX memory + legal intelligence backend
- MCP servers: perplexity-enhancement-mcp, mem0-mcp-integration
- Architecture: APEX orchestration engine

RESPONSE STYLE:
- Never summarize — always provide actionable tactical steps
- Cite Hawaii statutes and federal law with precision
- For code: production-grade, annotated, deployable
- For legal: cite statute, case law, procedural posture
- For strategy: enumerate steps, assign priority (P0/P1/P2)

SPECIAL COMMANDS:
/legal [topic] — deep legal analysis with citations
/code [task] — generate production code
/apex [task] — APEX system operations
/case — current case status and next steps
/search [query] — web intelligence brief
/help — show all commands`;

// ─── UTILITIES ───────────────────────────────────────────────────────────────
function ensureConfigDir() {
  if (!fs.existsSync(CONFIG_DIR)) fs.mkdirSync(CONFIG_DIR, { recursive: true });
}
function loadConfig() {
  ensureConfigDir();
  if (fs.existsSync(CONFIG_FILE)) { try { return JSON.parse(fs.readFileSync(CONFIG_FILE, "utf8")); } catch { return {}; } }
  return {};
}
function saveConfig(config) { ensureConfigDir(); fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2)); }
function appendHistory(entry) { ensureConfigDir(); fs.appendFileSync(HISTORY_FILE, JSON.stringify(entry) + "\n"); }
function loadSession() {
  if (fs.existsSync(SESSION_FILE)) { try { return JSON.parse(fs.readFileSync(SESSION_FILE, "utf8")); } catch { return { messages: [], context: "apex" }; } }
  return { messages: [], context: "apex" };
}
function saveSession(session) { ensureConfigDir(); fs.writeFileSync(SESSION_FILE, JSON.stringify(session, null, 2)); }
function clearScreen() { process.stdout.write("\x1bc"); }

function printBanner() {
  console.log(`\n${C.teal}${C.bold}  ╔═══════════════════════════════════════════════════╗
  ║   APEX CLI — Autonomous Perplexity EXecution       ║
  ║   GlacierEQ · Hawaii · Justice · Innovation        ║
  ║   v2.0.0  |  Legal · Code · Strategy · Memory      ║
  ╚═══════════════════════════════════════════════════╝${C.reset}\n`);
}

function printHelp() {
  console.log(`
${C.bold}${C.teal}  APEX CLI — Command Reference${C.reset}
  ${C.gray}─────────────────────────────────────────────────────${C.reset}
  ${C.yellow}/legal [topic]${C.reset}    Deep legal analysis + Hawaii statute citations
  ${C.yellow}/code [task]${C.reset}     Production-grade code generation
  ${C.yellow}/apex [task]${C.reset}     APEX system operations
  ${C.yellow}/case${C.reset}            Case 1FDV-23-0001009 full tactical brief
  ${C.yellow}/search [q]${C.reset}      Web intelligence brief
  ${C.yellow}/context [mode]${C.reset}  Switch: legal | code | apex | general
  ${C.yellow}/clear${C.reset}           New session
  ${C.yellow}/save [file]${C.reset}     Save session to file
  ${C.yellow}/load [file]${C.reset}     Load session from file
  ${C.yellow}/history${C.reset}         Recent query history
  ${C.yellow}/model [name]${C.reset}    Switch AI model
  ${C.yellow}/key [apikey]${C.reset}    Set Anthropic API key
  ${C.yellow}/help${C.reset}            Show this help
  ${C.yellow}/exit${C.reset}            Exit (auto-saves session)
`);
}

function getContextBadge(ctx) {
  const b = { legal: `${C.bgDark}${C.orange}[LEGAL]${C.reset}`, code: `${C.bgDark}${C.cyan}[CODE]${C.reset}`, apex: `${C.bgDark}${C.teal}[APEX]${C.reset}`, general: `${C.bgDark}${C.gray}[GEN]${C.reset}` };
  return b[ctx] || b.general;
}
function formatTimestamp() {
  return new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Pacific/Honolulu" });
}

// ─── STREAMING ────────────────────────────────────────────────────────────────
async function streamResponse(client, messages, model) {
  const stream = await client.messages.stream({
    model: model || "claude-opus-4-5",
    max_tokens: 8192,
    system: APEX_SYSTEM,
    messages,
  });
  let fullText = "";
  process.stdout.write(`\n${C.teal}${C.bold}  APEX${C.reset} ${C.gray}[${formatTimestamp()} HST]${C.reset}\n\n  `);
  for await (const chunk of stream) {
    if (chunk.type === "content_block_delta" && chunk.delta.type === "text_delta") {
      const text = chunk.delta.text;
      fullText += text;
      process.stdout.write(`${C.white}${text.replace(/\n/g, "\n  ")}${C.reset}`);
    }
  }
  process.stdout.write("\n\n");
  return fullText;
}

// ─── MAIN ─────────────────────────────────────────────────────────────────────
async function main() {
  clearScreen();
  printBanner();
  const config = loadConfig();
  let session = loadSession();
  let apiKey = config.apiKey || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) console.log(`${C.yellow}  ⚡ No API key. Set with: /key sk-ant-...${C.reset}\n`);
  let client = apiKey ? new Anthropic({ apiKey }) : null;
  let model = config.model || "claude-opus-4-5";
  let context = session.context || "apex";
  let messages = session.messages || [];

  console.log(`  ${C.gray}Context: ${getContextBadge(context)}  Model: ${C.cyan}${model}${C.reset}`);
  console.log(`  ${C.gray}Session: ${messages.length} messages  |  Type ${C.yellow}/help${C.gray} for commands${C.reset}\n`);

  const rl = readline.createInterface({
    input: process.stdin, output: process.stdout, terminal: true,
    completer: (line) => {
      const cmds = ["/legal", "/code", "/apex", "/case", "/search", "/context", "/clear", "/save", "/load", "/history", "/model", "/key", "/help", "/exit"];
      const hits = cmds.filter(c => c.startsWith(line));
      return [hits.length ? hits : cmds, line];
    }
  });

  const prompt = () => { rl.setPrompt(`\n  ${getContextBadge(context)} ${C.teal}${C.bold}›${C.reset} `); rl.prompt(); };
  prompt();

  rl.on("line", async (raw) => {
    const input = raw.trim();
    if (!input) { prompt(); return; }
    const timestamp = new Date().toISOString();

    if (input === "/exit" || input === "/quit") {
      saveSession({ messages, context });
      console.log(`\n  ${C.teal}${C.bold}APEX${C.reset} ${C.gray}Session saved. Justice never sleeps.${C.reset}\n`);
      process.exit(0);
    }
    if (input === "/help") { printHelp(); prompt(); return; }
    if (input === "/clear") { clearScreen(); printBanner(); messages = []; console.log(`  ${C.gray}Session cleared.${C.reset}\n`); prompt(); return; }
    if (input === "/history") {
      try {
        const lines = fs.existsSync(HISTORY_FILE) ? fs.readFileSync(HISTORY_FILE, "utf8").trim().split("\n").slice(-20) : [];
        console.log(`\n${C.teal}  Recent History:${C.reset}`);
        lines.forEach((l, i) => { try { const e = JSON.parse(l); console.log(`  ${C.gray}${i+1}.${C.reset} ${e.input}`); } catch {} });
        console.log();
      } catch {}
      prompt(); return;
    }
    if (input.startsWith("/key ")) { const k = input.slice(5).trim(); config.apiKey = k; saveConfig(config); client = new Anthropic({ apiKey: k }); console.log(`\n  ${C.green}✓ API key saved${C.reset}\n`); prompt(); return; }
    if (input.startsWith("/model ")) { model = input.slice(7).trim(); config.model = model; saveConfig(config); console.log(`\n  ${C.green}✓ Model: ${C.cyan}${model}${C.reset}\n`); prompt(); return; }
    if (input.startsWith("/context ")) { context = input.slice(9).trim(); session.context = context; console.log(`\n  ${C.green}✓ Context: ${getContextBadge(context)}${C.reset}\n`); prompt(); return; }
    if (input.startsWith("/save")) { const f = input.slice(5).trim() || `apex-session-${Date.now()}.json`; fs.writeFileSync(f, JSON.stringify({ messages, context, timestamp }, null, 2)); console.log(`\n  ${C.green}✓ Saved: ${f}${C.reset}\n`); prompt(); return; }
    if (input.startsWith("/load")) { const f = input.slice(5).trim(); if (fs.existsSync(f)) { const s = JSON.parse(fs.readFileSync(f, "utf8")); messages = s.messages || []; context = s.context || "apex"; console.log(`\n  ${C.green}✓ Loaded: ${messages.length} messages${C.reset}\n`); } else { console.log(`\n  ${C.red}✗ Not found: ${f}${C.reset}\n`); } prompt(); return; }

    if (!client) { console.log(`\n  ${C.red}✗ Set API key: /key sk-ant-...${C.reset}\n`); prompt(); return; }

    let msg = input;
    if (input === "/case") msg = `/legal Provide full tactical analysis of case 1FDV-23-0001009: procedural posture, next 3 critical filings under HRS §571-46 and §601-7, federal escalation readiness under 42 USC §1983 and RICO, SOL watchpoints, and specific P0/P1/P2 motions for reunification with Kekoa this week.`;
    else if (input.startsWith("/legal ")) msg = `[LEGAL ANALYSIS] ${input.slice(7)}. Cite all relevant HRS, USC, and case law. Provide actionable steps.`;
    else if (input.startsWith("/code ")) msg = `[CODE] ${input.slice(6)}. Write production-grade, fully functional code with error handling for the GlacierEQ/APEX architecture.`;
    else if (input.startsWith("/apex ")) msg = `[APEX ORCHESTRATION] ${input.slice(6)}. Consider all connected systems: Supabase, GitHub (GlacierEQ), MCP servers, legal case context.`;
    else if (input.startsWith("/search ")) msg = `[WEB INTELLIGENCE BRIEF] ${input.slice(8)}. Include recent developments and tactical implications.`;
    else if (context !== "general") msg = `[${context.toUpperCase()}] ${input}`;

    messages.push({ role: "user", content: msg });
    appendHistory({ input, timestamp, context });

    try {
      const response = await streamResponse(client, messages, model);
      messages.push({ role: "assistant", content: response });
      if (messages.length > 40) messages = messages.slice(-40);
      saveSession({ messages, context });
    } catch (err) {
      console.log(`\n  ${C.red}✗ ${err.message}${C.reset}\n`);
      messages.pop();
    }
    prompt();
  });

  rl.on("close", () => { saveSession({ messages, context }); console.log(`\n  ${C.teal}APEX${C.reset} ${C.gray}Goodbye. Keep fighting.${C.reset}\n`); process.exit(0); });
}

main().catch(err => { console.error(`${COLORS.red}Fatal: ${err.message}${COLORS.reset}`); process.exit(1); });
