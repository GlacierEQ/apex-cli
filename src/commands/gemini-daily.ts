#!/usr/bin/env ts-node
/**
 * APEX Gemini Daily Brief
 * Case 1FDV-23-0001009
 *
 * Reads output/tactical-plan.json (written by daily-protocol pipeline)
 * and asks Gemini to produce a tactical narrative with:
 *   - Primary action with legal theory
 *   - Deadline warnings
 *   - Federal escalation next step
 *   - Reunification status
 *
 * Usage:
 *   npx ts-node src/commands/gemini-daily.ts
 *   npx ts-node src/commands/gemini-daily.ts --model pro
 */
import fs from 'fs';
import path from 'path';
import { route } from '../models/router';
import dotenv from 'dotenv';
dotenv.config();

const modelArg = process.argv.includes('--model')
  ? process.argv[process.argv.indexOf('--model') + 1]
  : 'flash';

async function main() {
  const planPath = path.resolve(process.cwd(), 'output', 'tactical-plan.json');

  if (!fs.existsSync(planPath)) {
    console.error('tactical-plan.json not found. Run /apex-daily first.');
    process.exit(1);
  }

  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));

  const prompt = `
Case 1FDV-23-0001009 — APEX Daily Tactical Brief

Tactical plan data:
${JSON.stringify(plan, null, 2)}

Provide:
1. PRIMARY ACTION — most important single step today, with statute/case citation
2. DEADLINE WARNINGS — anything < 7 days with rule reference
3. FEDERAL ESCALATION — what to do at Stage ${plan.federal_escalation_stage} today
4. EVIDENCE GAPS — address the ${plan.sha256_null_count} exhibits missing SHA-256
5. KEKOA STATUS — reunification delta assessment
6. COST OF INACTION — one sentence

No summaries. Court-ready language. Cite HRS §571-46, §1983, constitutional authority.
`.trim();

  console.log('\n■ APEX GEMINI DAILY BRIEF\n');
  await route({ task: 'chat', content: prompt, forceModel: modelArg === 'pro' ? 'gemini-pro' : 'gemini-flash', stream: true });
  console.log();
}

main().catch((e) => { console.error(e); process.exit(1); });
