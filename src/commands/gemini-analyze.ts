#!/usr/bin/env ts-node
/**
 * APEX Gemini Analyze — Pipe documents / transcripts for AI analysis
 * Case 1FDV-23-0001009
 *
 * Usage:
 *   # Analyze a file
 *   npx ts-node src/commands/gemini-analyze.ts --file hearing.txt --task summarize
 *
 *   # Analyze stdin pipe
 *   cat exhibit.txt | npx ts-node src/commands/gemini-analyze.ts --task exhibit-review
 *
 *   # Research a question
 *   npx ts-node src/commands/gemini-analyze.ts --task research --query "HRCP 60(b) standard Hawaii"
 *
 *   # Draft a motion section
 *   npx ts-node src/commands/gemini-analyze.ts --task draft --query "Relief under HRS 571-46(b)"
 */
import fs from 'fs';
import { route } from '../models/router';
import dotenv from 'dotenv';
dotenv.config();

const args = process.argv.slice(2);
const get  = (flag: string) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : null; };

const task  = get('--task')  ?? 'analyze';
const file  = get('--file');
const query = get('--query');
const model = get('--model') ?? 'flash';

async function main() {
  let content = '';

  if (file) {
    content = fs.readFileSync(file, 'utf8');
  } else if (query) {
    content = query;
  } else if (!process.stdin.isTTY) {
    content = fs.readFileSync('/dev/stdin', 'utf8');
  } else {
    console.error('Provide --file, --query, or pipe content via stdin');
    process.exit(1);
  }

  const result = await route({
    task: task as any,
    content,
    forceModel: model === 'pro' ? 'gemini-pro' : 'gemini-flash'
  });

  console.log(result.output);
  console.error(`\n[${result.model} | ${task} | ${result.durationMs}ms]`);
}

main().catch((e) => { console.error(e); process.exit(1); });
