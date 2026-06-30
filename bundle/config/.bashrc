# ╔══════════════════════════════════════════════════════════════════╗
# ║  APEX SYSTEM BASHRC — MAXIMUM BOOTUP + PRO-CODE                ║
# ║  Source'd directly (no subshells) for <100ms startup            ║
# ╚══════════════════════════════════════════════════════════════════╝

# ── PATH (single export, no duplicates) ──────────────────────────
export PATH="$HOME/bin:$HOME/.local/bin:$HOME/.mimocode/bin:$HOME/.bun/bin:$HOME/.grok/bin:$PATH"

# ── APEX Core Environment ────────────────────────────────────────
export APEX_VERBOSE=0
export APEX_ROOT_CHECKPOINT="30db1e4f"
export APEX_POINTER_INDEX="$HOME/APEX_POINTER_INDEX.json"
export PROOT_NO_SECCOMP=1
export TOKEN_SAVINGS_ENABLED=true
export HYPER_EFFICIENCY_FLOW=true
export SURGICAL_MODE=true

# ── Load Sovereign Environment Keys ───────────────────────────────
[[ -f "$HOME/.gemini_keys" ]] && source "$HOME/.gemini_keys"

# ── Memory Prime (Supermemory + Mem0 token savings) ─────────────
alias prime-ctx='cat "$HOME/.supermemory/ops/live-context.md" 2>/dev/null || echo "Run: apex-prime \"your task\""'
export APEX_LIVE_CONTEXT="$HOME/.supermemory/ops/live-context.md"
alias apex-ready='apex-grok-ready'

# ── Performance Tuning (from apex_terminal_maximize.sh) ───────────
export OMP_NUM_THREADS=$(nproc)
export OPENBLAS_NUM_THREADS=$(nproc)
export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=65536
export MALLOC_TRIM_THRESHOLD_=65536
export AEON_MAX_POWER=1
export AEON_TOKEN_CACHE_HIT=88.2

# ── Pro-Code Identity (from pro_code/CODER-SKILL.md) ─────────────
export PRO_CODE_VERSION="1.1"
export PRO_CODE_MANTRA="Two strands. One sovereign DNA."
export PRO_CODE_STYLE="production-grade, not prototype"
export PRO_CODE_PHILOSOPHY="One Big Push — never fragment what belongs together"

ulimit -n 16384 2>/dev/null || true

# ── Git Optimization (from apex_system_maximizer.sh) ──────────────
git config --global core.compression 9 2>/dev/null
git config --global http.postBuffer 524288000 2>/dev/null
git config --global core.packedGitLimit 512m 2>/dev/null
git config --global core.packedGitWindowSize 512m 2>/dev/null
git config --global pack.deltaCacheSize 512m 2>/dev/null
git config --global pack.packSizeLimit 512m 2>/dev/null
git config --global pack.windowMemory 512m 2>/dev/null

# ── Termux Optimization (from apex_terminal_maximize.sh) ──────────
mkdir -p ~/.termux
cat << 'PROPS' > ~/.termux/termux.properties
allow-external-apps = true
terminal-transcript-rows = 10000
terminal-cursor-blink-rate = 500
terminal-cursor-style = bar
extra-keys = [['ESC','/','-','HOME','UP','END','PGUP'], \
              ['TAB','CTRL','ALT','LEFT','DOWN','RIGHT','PGDN']]
fullscreen = true
back-key = escape
PROPS
termux-wake-lock 2>/dev/null || true

# ── Agent CLI Configs (from apex_cli_maximize.sh, inline) ─────────
mkdir -p ~/.config/antigravity ~/.mastermind ~/.config/goose ~/.config/codex ~/.config/gemini ~/.openclaw

cat << 'YAML' > ~/.config/antigravity/config.yaml
optimization_mode: "MAXIMUM_SAVINGS"
token_cache: true
model: "gemini-2.0-flash-exp"
parallel_execution: true
max_threads: 16
memory_connector: "mem0+pinecone"
YAML

cat << 'JSON' > ~/.mastermind/config.json
{"default_model":"gemini-2.0-flash-exp","orchestration_level":"pro","concurrency":32,"telemetry":false}
JSON

cat << 'JSON' > ~/.config/goose/config.json
{"max_context_tokens":128000,"cache_enabled":true,"cache_hit_target":0.88,"profile":"pro-heavy","telemetry":false}
JSON

cat << 'JSON' > ~/.config/codex/settings.json
{"engine":"davinci-codex-max","temperature":0.0,"max_tokens":8192,"top_p":1.0,"frequency_penalty":0.2}
JSON

cat << 'TOML' > ~/.config/gemini/config.toml
[model]
name = "gemini-1.5-pro-latest"
system_instruction = "You are AEON-777, maximized for heavy token efficiency and pro logic."
temperature = 0.1
context_caching = true
TOML

cat << 'JSON' > ~/.openclaw/openclaw.json
{"gateway":{"port":19000,"host":"127.0.0.1","cache_enabled":true},"agent":{"model":"gemini-2.0-flash-exp","provider":"google","max_context_tokens":1000000,"threading_mode":"max-performance"},"ui":{"theme":"pro-dark","compact_mode":true}}
JSON

# ── Aliases ──────────────────────────────────────────────────────
alias apex-max='bash ~/.apex_system_maximizer.sh'
alias agy-max='bash ~/.apex_cli_maximize.sh'
alias term-max='bash ~/.apex_terminal_maximize.sh'
alias desktop-max='bash ~/.start-desktop.sh'
alias mastermind='mastermind-pro'
alias openclaw='npx -y openclaw'
alias ll='ls -la'
alias mission-status='cat ~/MISSIONS/AEON_777/aeon-777-mission-state.json'
alias todo='cat ~/APEX_COMMAND_CENTER/01_MASTER_TRUTH_INDEX.md'

# ── Ollama Local Models ──────────────────────────────────────────
alias run-gemma4='ollama run gemma4:SUPREME_REASONING'
alias run-microwave='ollama run stealth-microwave:latest'
alias run-supernova='ollama run stealth-supernova:latest'
alias run-claw='ollama run stealth-claw:latest'
alias run-mastermind='ollama run mastermind:latest'

# ── Agent Wrappers (token savings injection) ─────────────────────
gemini() { export TOKEN_SAVINGS_ENABLED=true HYPER_EFFICIENCY_FLOW=true SURGICAL_MODE=true; command gemini "$@"; }
agy() { export TOKEN_SAVINGS_ENABLED=true HYPER_EFFICIENCY_FLOW=true SURGICAL_MODE=true; command agy "$@"; }
mimo() { export TOKEN_SAVINGS_ENABLED=true HYPER_EFFICIENCY_FLOW=true SURGICAL_MODE=true; command mimo-ops "$@"; }
mimocode() { mimo "$@"; }

# ── Grok Completions ─────────────────────────────────────────────
[[ -r "$HOME/.grok/completions/bash/grok.bash" ]] && source "$HOME/.grok/completions/bash/grok.bash"
export NOTION_API_KEY="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"


# >>> grok installer >>>
[[ -r "$HOME/.grok/completions/bash/grok.bash" ]] && source "$HOME/.grok/completions/bash/grok.bash"
# <<< grok installer <<<
# APEX saved startup state (CoreMaximized token savings)
[ -f "$HOME/.apex/session_boot.env" ] && source "$HOME/.apex/session_boot.env"
export APEX_STARTUP_STATE="$HOME/.apex/STARTUP_STATE.json"
export GITHUB_TOKEN="github_pat_11BOJ6ZOA0UzG7G12gTS4a_b5kmvZdRF2nrlYuMP7woB9zmHD8QEH0tLrWVUXTkTbW2RULXVURHORUFS7"
export GITHUB_TOKEN="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"
# Load Google Keep keys on startup
source ~/bin/sync-keys.sh 2>/dev/null
