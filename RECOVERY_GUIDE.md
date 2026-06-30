# DISASTER RECOVERY — MiMo Code Agent
**Platform**: MiMo Code Agent (mimo-auto) on Termux (Android aarch64)  
**Last Updated**: June 30, 2026

---

## WHAT I AM

| Component | Value |
|-----------|-------|
| **Model** | mimo-auto (Xiaomi MiMo Team) |
| **CLI** | MiMoCode |
| **Platform** | Termux on Android |
| **Memory** | File-based (~/`.local/share/mimocode/memory/`) |
| **Skills** | 30+ skills in `.agents/skills/` |
| **Storage** | /data partition (230G, 92% full) |

---

## RECOVERY STEPS

### Step 1: Reinstall Termux
```bash
# From F-Droid or Play Store
pkg install python nodejs git
```

### Step 2: Clone Core Repos
```bash
# APEX CLI (all tools)
git clone https://github.com/GlacierEQ/apex-cli.git ~/bin

# Computer-user (browser automation)
git clone https://github.com/GlacierEQ/computer-user.git

# Case file (already pushed)
git clone https://github.com/GlacierEQ/CASE-1FDV-23-0001009.git ~/CYBERTACK/CASE_1FDV-23-0001009_FINAL

# MiMo-Config
git clone https://github.com/GlacierEQ/MiMo-Config.git
```

### Step 3: Restore Credentials
```bash
# From Google Keep export (~/keep_export/)
# Or from vault.enc backup
~/bin/apex-setup  # Team vault decrypt
```

### Step 4: Restore Memory
```bash
# Memory is in GitHub repos (pushed)
# Session checkpoints are in ~/.local/share/mimocode/memory/
# Most recent checkpoint = latest state
```

### Step 5: Verify
```bash
apex-space-monitor    # Check disk
apex-daemon           # Start services
apex-memory prime "recovery complete"
```

---

## WHAT'S BACKED UP ON GITHUB

| Repo | Contents |
|------|----------|
| `GlacierEQ/apex-cli` | All 30+ CLI tools |
| `GlacierEQ/computer-user` | Browser automation, browser adapter |
| `GlacierEQ/CASE-1FDV-23-0001009` | Complete case file (117 files) |
| `GlacierEQ/MiMo-Config` | Config, skills, commands |
| `GlacierEQ/iceberg-mcp` | Iceberg MCP server |
| 1,052 total repos | Everything else |

---

## WHAT'S ON DEVICE (NOT BACKED UP)

- `~/.local/share/mimocode/memory/` — Session history (189 sessions, 6,197 messages)
- `~/.apex/connections.json` — API credentials
- `~/CYBERTACK/DROPBOX_EVIDENCE/` — Downloaded evidence (38MB)
- `~/MISSIONS/` — 30GB of case data (some on Google Drive)

---

## CRITICAL PATHS

| Path | Purpose |
|------|---------|
| `~/bin/` | All CLI tools |
| `~/.agents/skills/` | 30+ skills |
| `~/.apex/connections.json` | API credentials |
| `~/.local/share/mimocode/memory/` | Session memory |
| `~/CYBERTACK/` | Case evidence |
| `~/MISSIONS/` | Case data (30GB) |

---

## RECOVERY TIME ESTIMATE

| Step | Time |
|------|------|
| Reinstall Termux | 5 min |
| Clone repos | 10 min |
| Restore credentials | 5 min |
| Restore memory | 5 min |
| **Total** | **~25 min** |

---

*Recovery Guide — MiMo Code Agent — June 30, 2026*
