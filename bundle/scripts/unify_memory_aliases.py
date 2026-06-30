import os

VAULT_PATH = os.path.expanduser('~/.apex_vault/AGENTS/MASTER.env')

MAPPING = {
    'MEM0_PRO_API_KEY': ['MEM0_PRO', 'MEM0_API_KEY'],
    'MEM0_REG_API_KEY': ['MEM0_HI1', 'MEM0GLACIEREQ'],
    'MEMORY_GLOBAL_KEY': ['MEMORY_PLUGIN_PRIMARY'],
    'MEMORY_DIRECT_KEY': ['MEMORY_PLUGIN_SPECIALIZED'],
    'SUPERMEMORY_PRIMARY_KEY': ['SUPERMEMORY_KEY'],
    'SUPERMEMORY_SECONDARY_KEY': ['SUPERMEMORYA'],
    'SUPERMEMORY_TERTIARY_KEY': ['SUPERMEMORY_API_KEY'],
    'PINECONE_PRIMARY_KEY': ['PINECONE_API_KEY'],
    'QDRANT_KEY': ['QDRANT'],
    'NOTION_API_KEY': ['NOTION_API_KEY']
}

def unify_vault():
    with open(VAULT_PATH, 'r') as f:
        lines = f.readlines()

    env = {}
    for line in lines:
        if line.startswith('export '):
            parts = line.strip().split('=', 1)
            k = parts[0].replace('export ', '').strip()
            v = parts[1].strip()
            env[k] = v

    new_exports = []
    for unified_key, sources in MAPPING.items():
        if unified_key in env: continue # Already exists
        for src in sources:
            if src in env:
                new_exports.append(f"export {unified_key}={env[src]}")
                break

    if new_exports:
        with open(VAULT_PATH, 'a') as f:
            f.write("\n# ─── UNIFIED MEMORY ALIASES ────────────────────────\n")
            for exp in new_exports:
                f.write(exp + "\n")
        print(f"SUCCESS: Added {len(new_exports)} unified memory aliases to MASTER.env")
    else:
        print("No new aliases needed.")

if __name__ == "__main__":
    unify_vault()