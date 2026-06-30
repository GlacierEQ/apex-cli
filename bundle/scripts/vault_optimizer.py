import os
import re

# APEX MASTER VAULT STABILIZER V2.0
# Conservative parsing for pure shell compatibility.

VAULT_PATH = os.path.expanduser("~/.apex_vault/AGENTS/MASTER.env")

CATEGORIES = {
    "AI_LLM_CORE": ["OPENAI", "ANTHROPIC", "CLAUDE", "GEMINI", "DEEPSEEK", "GROQ", "XAI", "COHERE", "TOGETHER", "MINIMAX", "OLLAMA"],
    "MEMORY_VECTOR": ["MEM0", "SUPERMEMORY", "PINECONE", "QDRANT", "NEO4J", "MEMORY", "REDIS", "UPSTASH", "VALKEY"],
    "DEV_AGENT_TOOLS": ["AGENTOPS", "COMPOSIO", "MIMO", "BROWSERBASE", "E2B", "LANGCHAIN", "LETTA", "CODEGEN", "CODERABBIT", "CODY", "CURSOR", "WINDSURF"],
    "INFRA_CLOUD": ["AWS", "VERCEL", "RAILWAY", "SUPABASE", "CLOUDFLARE", "NETLIFY", "DOCKER", "RENDER", "FIREBASE", "NEON", "MONGODB", "PRISMA"],
    "FORENSIC_LEGAL": ["COURTLISTENER", "ZOTERO", "PDF4ME", "PDF_CO", "DOCUGENERATE", "DOCUPILOT", "PLAID", "TISANE", "NATIF"],
    "SOCIAL_COMMS_PRODUCTIVITY": ["SLACK", "DISCORD", "NOTION", "ASANA", "CLICKUP", "AIRTABLE", "JIRA", "CONFLUENCE", "TODOIST", "MAILCHIMP", "RESEND", "TWILIO", "STRIPE"],
    "GIT_REPOS": ["GITHUB", "GITLAB", "OVERLEAF", "POLYGIT"],
    "SYSTEM_INTERNAL": ["APEX", "AG_", "CHUNK", "OLLAMA", "PROOT", "DEBUG", "LOG", "FORMAT", "TIMEOUT", "MAX_"]
}

def get_category(key):
    for cat, markers in CATEGORIES.items():
        if any(marker in key for marker in markers):
            return cat
    return "UNCATEGORIZED_OR_MISC"

def is_valid_key(key):
    # Strictly alphanumeric/underscore, must start with alpha
    return re.match(r'^[A-Z][A-Z0-9_]{1,63}$', key) is not None

def is_garbage_val(val):
    # Filter out values that look like code or sentences
    if len(val) > 1000: return True
    if val.startswith('http') and ' ' in val: return True
    if '(' in val or ')' in val or '{' in val or '}' in val: return True
    return False

def stabilize_vault():
    if not os.path.exists(VAULT_PATH): return

    raw_env = {}
    with open(VAULT_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            
            # Extract key/val
            parts = line.split('=', 1)
            key = parts[0].strip().replace('-', '_').replace('.', '_').upper()
            
            # Clean key from leading junk
            while key and not key[0].isalpha():
                key = key[1:]
            
            if not is_valid_key(key): continue
            
            val = parts[1].strip().strip('"').strip("'").replace(',', '').replace(';', '')
            if is_garbage_val(val): continue
            if not val: continue

            # Deduplicate: latest longest value wins
            if key in raw_env:
                if len(val) >= len(raw_env[key]):
                    raw_env[key] = val
            else:
                raw_env[key] = val

    # Grouping
    organized = {cat: {} for cat in CATEGORIES.keys()}
    organized["UNCATEGORIZED_OR_MISC"] = {}

    for key, val in raw_env.items():
        cat = get_category(key)
        organized[cat][key] = val

    # Write
    with open(VAULT_PATH, 'w') as f:
        f.write("# ═══════════════════════════════════════════════════════════════\n")
        f.write("#  APEX SYSTEM ENVIRONMENT CONFIG — STABILIZED MASTER VAULT\n")
        f.write(f"#  TOTAL UNIQUE KEYS: {len(raw_env)}\n")
        f.write("# ═══════════════════════════════════════════════════════════════\n\n")

        for cat in organized:
            if organized[cat]:
                f.write(f"# ─── {cat} ─────────────────────────────────\n")
                for key in sorted(organized[cat].keys()):
                    # Wrap in single quotes for shell safety
                    f.write(f"export {key}='{organized[cat][key]}'\n")
                f.write("\n")

    print(f"SUCCESS: Vault Stabilized. Unique keys: {len(raw_env)}")

if __name__ == "__main__":
    stabilize_vault()