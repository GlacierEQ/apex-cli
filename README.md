# APEX CLI — Complete Runtime

Pro Code CLI suite for the APEX ecosystem. Everything needed to run, recover, and operate.

## Structure

```
apex-cli/
├── core/                    # Core runtime modules
│   ├── browser_adapter.py   # Universal browser backend
│   ├── paths.py             # Configurable path resolution
│   ├── connections.py       # Credential loader
│   ├── pipeline.py          # Pipeline runner (enforced execution)
│   ├── unified_memory_mcp.py # Memory MCP connector
│   ├── mimo_apex_sync.py    # MiMo-APEX sync
│   ├── mem0_master_apex.py  # Mem0 integration
│   ├── map_memory_unification.py # Memory unification
│   └── sync_case_os.py      # Case OS sync
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── apex-*                   # CLI tools (30+)
├── RECOVERY_GUIDE.md        # Disaster recovery
└── README.md                # This file
```

## CLI Tools

### System
| Command | Purpose |
|---------|---------|
| `apex-daemon` | APEX service daemon |
| `apex-monitor` | System health monitor |
| `apex-service` | Service management |
| `apex-auto-start` | Auto-start services |
| `apex-cron-setup` | Cron job setup |

### Space Management
| Command | Purpose |
|---------|---------|
| `apex-space-monitor` | Quick disk check + cleanup |
| `apex-space-manager` | Comprehensive report |
| `apex-space-daemon` | Hourly monitoring daemon |

### Memory & Sync
| Command | Purpose |
|---------|---------|
| `apex-memory` | Holographic memory access |
| `apex-memory-daemon` | Persistent memory bridge |
| `apex-prime` | Quick context prime |

### Infrastructure
| Command | Purpose |
|---------|---------|
| `apex-browser-adapter` | Universal browser backend |
| `apex-paths` | Configurable path resolution |
| `apex-dropbox-bridge` | Dropbox integration |
| `apex-dropbox-refresh` | Token refresh |

### Legal & Case
| Command | Purpose |
|---------|---------|
| `apex-legal` | Legal warfare tools |
| `apex-legal-consolidate` | Case consolidation |
| `apex-forensics` | Forensic operations |
| `apex-scan-placeholders` | Code quality scanner |

### Deployment
| Command | Purpose |
|---------|---------|
| `apex-deploy-agent` | Deploy agent |
| `apex-deploy-masterpiece` | Deploy masterpiece |
| `apex-deploy-omni` | Deploy omni agent |

## Core Modules

| Module | Purpose |
|--------|---------|
| `core/browser_adapter.py` | Universal browser (Tasklet/Puppeteer) |
| `core/paths.py` | Env-aware path resolution |
| `core/connections.py` | Credential loader |
| `core/pipeline.py` | Enforced execution pipeline |
| `core/unified_memory_mcp.py` | Memory MCP connector |
| `core/mimo_apex_sync.py` | MiMo-APEX synchronization |

## Installation

```bash
git clone https://github.com/GlacierEQ/apex-cli.git
cd apex-cli
chmod +x apex-*
cp apex-* ~/bin/
```

## Recovery

If everything breaks:
1. Reinstall Termux (5 min)
2. `git clone` this repo (10 min)
3. Restore credentials (5 min)
4. Memory auto-restores (5 min)

See `RECOVERY_GUIDE.md` for details.
