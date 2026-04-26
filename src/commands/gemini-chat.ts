#!/usr/bin/env ts-node
/**
 * APEX Gemini Chat — Interactive REPL
 * Case 1FDV-23-0001009
 *
 * Usage:
 *   npx ts-node src/commands/gemini-chat.ts
 *   npx ts-node src/commands/gemini-chat.ts --model pro
 *   npx ts-node src/commands/gemini-chat.ts --task research "What is the RICO continuity standard?"
 *
 * Keyboard shortcuts in REPL:
 *   /clear    — clear history
 *   /model    — toggle flash/pro
 *   /status   — case status snapshot
 *   /exit     — quit
 */
import * as readline from 'readline';
import { route, RouterRequest, RouterResult } from '../models/router';
import { GeminiMessage } from '../models/gemini';
import dotenv from 'dotenv';
dotenv.config();

const CYAN   = '\x1b[36m';
const GREEN  = '\x1b[32m';
const YELLOW = '\x1b[33m';
const RED    = '\x1b[31m';
const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';

function banner() {
  console.log(`
${BOLD}${CYAN}┌───────────────────────────────────────────────┐${RESET}
${BOLD}${CYAN}│    APEX-GEMINI — Legal Ops AI Terminal             │${RESET}
${BOLD}${CYAN}│    Case 1FDV-23-0001009 | Barton v. [OP]            │${RESET}
${BOLD}${CYAN}│    Win condition: Reunification with Kekoa           │${RESET}
${BOLD}${CYAN}└───────────────────────────────────────────────┘${RESET}

  ${YELLOW}Commands:${RESET} /clear  /model  /status  /exit
  ${YELLOW}Models:${RESET}   flash (fast) | pro (deep reasoning)
  ${YELLOW}Tasks:${RESET}    chat | research | summarize | draft | triage
`);
}

const CASE_STATUS = `
APEX Case Snapshot — 1FDV-23-0001009
──────────────────────────────────────
  Operator    : Casey Barton (Pro Se)
  Court       : Hawaiʻi Family Court, 1st Circuit
  Minor Child : Kekoa Barton
  Fed Stage   : 1 — Building state record
  Active Law  : HRS §571-46 | §1983 | RICO | XIV Amend.
  Obidian     : github.com/GlacierEQ/apex-obsidian-vault
  Registry    : github.com/GlacierEQ/apex-connector-registry
`;

async function runRepl(initialModel: 'flash' | 'pro' = 'flash') {
  banner();
  const history: GeminiMessage[] = [];
  let currentModel = initialModel;

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: `${GREEN}apex-gemini${RESET}(${YELLOW}${currentModel}${RESET})> `
  });

  rl.prompt();

  rl.on('line', async (line) => {
    const input = line.trim();
    if (!input) { rl.prompt(); return; }

    if (input === '/exit' || input === '/quit') { console.log('\nGoodbye.'); process.exit(0); }
    if (input === '/clear') { history.length = 0; console.log(`${YELLOW}History cleared.${RESET}`); rl.prompt(); return; }
    if (input === '/status') { console.log(CYAN + CASE_STATUS + RESET); rl.prompt(); return; }
    if (input === '/model') {
      currentModel = currentModel === 'flash' ? 'pro' : 'flash';
      console.log(`${YELLOW}Model switched to: ${currentModel}${RESET}`);
      rl.setPrompt(`${GREEN}apex-gemini${RESET}(${YELLOW}${currentModel}${RESET})> `);
      rl.prompt();
      return;
    }

    rl.pause();
    try {
      const req: RouterRequest = { task: 'chat', content: input, history, forceModel: `gemini-${currentModel}` as any, stream: true };
      console.log(`\n${CYAN}APEX-Gemini:${RESET}`);
      const result = await route(req);
      history.push({ role: 'user', text: input });
      history.push({ role: 'model', text: result.output });
      console.log(`\n${YELLOW}[${result.model} — ${result.durationMs}ms]${RESET}\n`);
    } catch (err: any) {
      console.error(`${RED}Error: ${err.message}${RESET}`);
    }
    rl.resume();
    rl.prompt();
  });
}

async function runOneShot(task: string, content: string, model?: string) {
  const req: RouterRequest = {
    task: task as any,
    content,
    forceModel: model?.includes('pro') ? 'gemini-pro' : 'gemini-flash'
  };
  const result = await route(req);
  console.log(result.output);
  process.exit(0);
}

// CLI argument parsing
const args = process.argv.slice(2);
const modelArg = args.includes('--model') ? args[args.indexOf('--model') + 1] : 'flash';
const taskArg  = args.includes('--task')  ? args[args.indexOf('--task')  + 1] : null;
const content  = taskArg ? args[args.indexOf('--task') + 2] : null;

if (taskArg && content) {
  runOneShot(taskArg, content, modelArg).catch((e) => { console.error(e); process.exit(1); });
} else {
  runRepl(modelArg === 'pro' ? 'pro' : 'flash').catch((e) => { console.error(e); process.exit(1); });
}
