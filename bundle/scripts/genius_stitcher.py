import os
import re

# APEX GENIUS STITCHER V1.0
# Heuristic-based key recovery from messy forensic exports.

RAW_PATH = os.path.expanduser("~/.apex_vault/AGENTS/MASTER.env")
STABILIZED_PATH = os.path.expanduser("~/.apex_vault/AGENTS/MASTER.env.final")

# Known key starts
KEY_PREFIXES = ["sk-proj-", "sk-ant-api03-", "AIzaSy", "github_pat_", "ghp_", "pcsk_", "m0-", "ntn_", "ak_", "pplx-", "sk-or-v1-", "ey"]

def extract_tokens(text):
    # This regex looks for strings that look like typical API tokens
    # (Alphanumeric + some symbols, length > 20)
    tokens = re.findall(r'[A-Za-z0-9\-_]{20,}', text)
    return tokens

def get_full_key(prefix, text):
    # Find the longest string starting with the prefix
    pattern = re.compile(re.escape(prefix) + r'[A-Za-z0-9\-_]+')
    matches = pattern.findall(text)
    if not matches: return None
    return max(matches, key=len)

def genius_stitch():
    with open(RAW_PATH, 'r') as f:
        full_content = f.read().replace('\n', ' ').replace(' ', '')

    recovered = {}
    
    # 1. Surgical Extraction of core keys
    recovered["OPENAI_API_KEY"] = get_full_key("sk-proj-", full_content)
    recovered["ANTHROPIC_API_KEY"] = get_full_key("sk-ant-api03-", full_content)
    recovered["GEMINI_API_KEY"] = get_full_key("AIzaSy", full_content)
    recovered["PINECONE_API_KEY"] = get_full_key("pcsk_", full_content)
    recovered["GITHUB_TOKEN"] = get_full_key("github_pat_", full_content) or get_full_key("ghp_", full_content)
    recovered["NOTION_API_KEY"] = get_full_key("ntn_", full_content)
    recovered["PERPLEXITY_API_KEY"] = get_full_key("pplx-", full_content)
    recovered["GROQ_API_KEY"] = get_full_key("gsk_", full_content)
    
    # Clean up
    final_keys = {k: v for k, v in recovered.items() if v}
    
    with open(STABILIZED_PATH, 'w') as f:
        f.write("# ===============================================================\n")
        f.write("#  APEX SYSTEM ENVIRONMENT CONFIG — GENIUS RECOVERED VAULT\n")
        f.write("# ===============================================================\n\n")
        for k, v in sorted(final_keys.items()):
            f.write(f"export {k}='{v}'\n")

    print(f"SUCCESS: Recovered {len(final_keys)} core keys with Genius Stitching.")
    for k in final_keys:
        print(f"  > {k}: {final_keys[k][:10]}...{final_keys[k][-5:]}")

if __name__ == "__main__":
    genius_stitch()