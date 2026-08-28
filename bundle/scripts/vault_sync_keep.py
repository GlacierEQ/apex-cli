import os
import re

keep_file = "/data/data/com.termux/files/home/MISSIONS/AEON_777/CORE_MISSION/AEON-BRAIN-777/02_EVIDENCE_VAULT/CONSOLIDATED_ARCHIVE/evidence/google_keep_extracted/goohlekeep2026.txt"
master_env = "/data/data/com.termux/files/home/.apex_vault/AGENTS/MASTER.env"


def parse_env(file_path):
    env = {}
    if not os.path.exists(file_path):
        return env
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    return env


def parse_keep(file_path):
    # Regex to catch key=val pairs, ignoring some noise
    pattern = re.compile(r"^([A-Za-z0-9_\s.-]+)=([A-Za-z0-9._:/-]+)")
    keep_keys = {}
    with open(file_path, "r") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                key, val = match.groups()
                # Normalize key
                key = key.strip().replace(" ", "_").upper()
                keep_keys[key] = val.strip()
    return keep_keys


current_env = parse_env(master_env)
new_keys = parse_keep(keep_file)

updates = 0
for key, val in new_keys.items():
    if key not in current_env or current_env[key] != val:
        current_env[key] = val
        updates += 1

if updates > 0:
    # Sort and write back
    with open(master_env, "w") as f:
        f.write("# ═══════════════════════════════════════════════════════════════\n")
        f.write("#  APEX SYSTEM ENVIRONMENT CONFIG — UNIFIED MASTER\n")
        f.write(f"#  LAST SYNC: {updates} UPDATES FROM GOOGLE KEEP 2026\n")
        f.write("# ═══════════════════════════════════════════════════════════════\n\n")
        for key in sorted(current_env.keys()):
            f.write(f"{key}={current_env[key]}\n")
    print(f"SUCCESS: {updates} keys updated/added to MASTER.env")
else:
    print("No new updates found.")
