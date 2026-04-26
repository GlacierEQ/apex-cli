/**
 * APEX Gemini Adapter
 * Case 1FDV-23-0001009
 *
 * Wraps @google/generative-ai (Gemini 2.0 Flash / Pro)
 * Provides:
 *   - gemini.chat()        — streaming chat with legal system prompt
 *   - gemini.analyze()     — single-shot document/exhibit analysis
 *   - gemini.draft()       — motion section drafting
 *   - gemini.summarize()   — transcript / hearing summary
 *   - gemini.research()    — statute / case law synthesis
 */
import { GoogleGenerativeAI, GenerativeModel, Content } from '@google/generative-ai';

const SYSTEM_PROMPT = `You are APEX-Gemini, a precision legal-ops AI for Case 1FDV-23-0001009 (Barton v. [OP]), Hawaii Family Court.

Core mission: Constitutional warfare + reunification with Kekoa.

Rules:
1. No summaries. Court-ready, citation-precise, tactically actionable output only.
2. Every legal claim cites authority (statute or case).
3. Every fact cites an exhibit ID when available.
4. Federal escalation (§1983 / RICO) is always active — identify escalation opportunities.
5. Evaluate every ruling for HRCP 60(b), appeal, or federal attack potential.
6. Best-interest factors (HRS §571-46) always applied.
7. Reunification is the win condition.

Governing law: XIV Amend., §1983, RICO; Troxel; Santosky; Stanley;
9th Cir: Wallis, Keates, Moreland, H.J. Inc.;
Hawaiʻi: HRS §571-46, §571-46.4, §92F, HRE 901, HRCP 60(b), HPR 9; HRPC 3.3, 8.3, 8.4.`;

let _client: GoogleGenerativeAI | null = null;
let _flash: GenerativeModel | null = null;
let _pro: GenerativeModel | null = null;

function getClient() {
  if (!_client) {
    const key = process.env.GEMINI_API_KEY;
    if (!key) throw new Error('GEMINI_API_KEY not set');
    _client = new GoogleGenerativeAI(key);
    _flash = _client.getGenerativeModel({
      model: 'gemini-2.0-flash',
      systemInstruction: SYSTEM_PROMPT
    });
    _pro = _client.getGenerativeModel({
      model: 'gemini-2.0-pro-exp',
      systemInstruction: SYSTEM_PROMPT
    });
  }
  return { flash: _flash!, pro: _pro! };
}

export interface GeminiMessage { role: 'user' | 'model'; text: string; }

export interface AnalyzeResult {
  model: string;
  input_chars: number;
  output: string;
  tokens?: number;
}

export async function chat(
  history: GeminiMessage[],
  userMessage: string,
  opts?: { model?: 'flash' | 'pro'; stream?: boolean }
): Promise<string> {
  const { flash, pro } = getClient();
  const model = opts?.model === 'pro' ? pro : flash;

  const contents: Content[] = history.map((m) => ({
    role: m.role,
    parts: [{ text: m.text }]
  }));

  const chat = model.startChat({ history: contents });

  if (opts?.stream) {
    const stream = await chat.sendMessageStream(userMessage);
    let out = '';
    for await (const chunk of stream.stream) {
      const text = chunk.text();
      process.stdout.write(text);
      out += text;
    }
    process.stdout.write('\n');
    return out;
  }

  const result = await chat.sendMessage(userMessage);
  return result.response.text();
}

export async function analyze(content: string, task: string, model: 'flash' | 'pro' = 'flash'): Promise<AnalyzeResult> {
  const { flash, pro } = getClient();
  const m = model === 'pro' ? pro : flash;
  const prompt = `TASK: ${task}\n\nCONTENT:\n${content}`;
  const result = await m.generateContent(prompt);
  return {
    model: `gemini-2.0-${model}`,
    input_chars: content.length,
    output: result.response.text(),
    tokens: result.response.usageMetadata?.totalTokenCount
  };
}

export async function draft(section: string, context: string): Promise<string> {
  return analyze(context, `Draft the following motion section for Case 1FDV-23-0001009: ${section}. Cite HRS §571-46 and constitutional authority. Every factual assertion must reference an exhibit ID.`, 'pro').then(r => r.output);
}

export async function summarize(transcript: string): Promise<string> {
  return analyze(transcript, 'Summarize this hearing transcript for Case 1FDV-23-0001009. Extract: (1) rulings, (2) federal issues preserved, (3) due process violations, (4) HRS §571-46 factor arguments, (5) misconduct observations. Output as structured Markdown.', 'flash').then(r => r.output);
}

export async function research(query: string): Promise<string> {
  return analyze(query, `Research the following legal question for Case 1FDV-23-0001009. Cite primary authority. Identify HRS §571-46 factors, §1983 angles, and RICO patterns where applicable.`, 'pro').then(r => r.output);
}
