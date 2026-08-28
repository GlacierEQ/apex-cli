import os

VAULT_PATH = os.path.expanduser("~/.apex_vault/AGENTS/MASTER.env")
doc_path = os.path.expanduser("~/.apex_vault/AGENTS/MEMORY_UNIFICATION_MAP.md")

with open(VAULT_PATH, "r") as f:
    lines = f.readlines()

env = {}
for line in lines:
    line = line.strip()
    if line.startswith("export "):
        k, v = line.split("=", 1)
        env[k.replace("export ", "").strip()] = v.strip().strip("'")

mapping = {
    "MEM0_PRO_API_KEY": env.get("MEM0_PRO", env.get("MEM0_API_KEY")),
    "MEM0_REG_API_KEY": env.get("MEM0_HI1", env.get("MEM0GLACIEREQ")),
    "MEMORY_GLOBAL_KEY": env.get("MEMORY_PLUGIN_PRIMARY"),
    "MEMORY_DIRECT_KEY": env.get("MEMORY_PLUGIN_SPECIALIZED"),
    "SUPERMEMORY_PRIMARY_KEY": env.get("SUPERMEMORY_KEY"),
    "SUPERMEMORY_SECONDARY_KEY": env.get("SUPERMEMORYA"),
    "SUPERMEMORY_TERTIARY_KEY": env.get("SUPERMEMORY_API_KEY"),
    "PINECONE_PRIMARY_KEY": env.get("PINECONE_API_KEY"),
    "QDRANT_KEY": env.get("QDRANT_KEY"),
    "NOTION_API_KEY": env.get("NOTION_API_KEY"),
}

with open(doc_path, "w") as f:
    f.write("# 🧠 APEX MEMORY UNIFICATION MAP\n\n")
    f.write(
        "This document maps the existing APEX Vault keys to the standardized Unified Memory Connect interface.\n\n"
    )
    f.write("| Unified Variable | Vault Source Value (Truncated) | Status |\n")
    f.write("| :--- | :--- | :--- |\n")
    for k, v in mapping.items():
        val_str = f"`{v[:15]}...`" if v else "N/A"
        status = "✅ MAPPED" if v else "❌ MISSING"
        f.write(f"| `{k}` | {val_str} | {status} |\n")

    f.write("\n## 🛠️ Unification Action Plan\n")
    f.write(
        "1. **Aliasing**: Standardize these variable names in the `~/.apex_vault/AGENTS/MASTER.env` for cross-agent compatibility.\n"
    )
    f.write(
        "2. **Connector Deployment**: Launch the `unified_memory_mcp.py` server to bridge these layers.\n"
    )
    f.write(
        "3. **Consistency Check**: Run `verify_mem0_layers.py` to ensure all 6 layers are responsive.\n"
    )

print(f"SUCCESS: Memory Unification Map created at {doc_path}")
