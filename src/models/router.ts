/**
 * APEX Multi-Model Router
 * Case 1FDV-23-0001009
 *
 * Routes legal-ops AI tasks to the best model:
 *   gemini-flash  — speed: triage, summaries, deadline scans
 *   gemini-pro    — depth: motion drafting, research, federal strategy
 *   (extensible)  — add Claude, GPT-4o, Grok slots as needed
 */
import * as Gemini from './gemini';

export type ModelSlot = 'gemini-flash' | 'gemini-pro';

export interface RouterRequest {
  task:
    | 'chat'
    | 'analyze'
    | 'draft'
    | 'summarize'
    | 'research'
    | 'triage'
    | 'exhibit-review'
    | 'motion-section'
    | 'federal-memo';
  content: string;
  history?: Gemini.GeminiMessage[];
  forceModel?: ModelSlot;
  stream?: boolean;
}

export interface RouterResult {
  model: ModelSlot;
  task: RouterRequest['task'];
  output: string;
  durationMs: number;
}

const TASK_MODEL_MAP: Record<RouterRequest['task'], ModelSlot> = {
  'chat':           'gemini-flash',
  'triage':         'gemini-flash',
  'summarize':      'gemini-flash',
  'analyze':        'gemini-flash',
  'exhibit-review': 'gemini-flash',
  'draft':          'gemini-pro',
  'research':       'gemini-pro',
  'motion-section': 'gemini-pro',
  'federal-memo':   'gemini-pro'
};

export async function route(req: RouterRequest): Promise<RouterResult> {
  const start = Date.now();
  const model = req.forceModel ?? TASK_MODEL_MAP[req.task];
  const geminiModel = model === 'gemini-pro' ? 'pro' : 'flash';

  let output: string;

  switch (req.task) {
    case 'chat':
      output = await Gemini.chat(req.history ?? [], req.content, { model: geminiModel, stream: req.stream });
      break;
    case 'summarize':
      output = await Gemini.summarize(req.content);
      break;
    case 'draft':
    case 'motion-section':
      output = await Gemini.draft(req.task, req.content);
      break;
    case 'research':
    case 'federal-memo':
      output = await Gemini.research(req.content);
      break;
    default:
      const r = await Gemini.analyze(req.content, req.task, geminiModel);
      output = r.output;
  }

  return { model, task: req.task, output, durationMs: Date.now() - start };
}
