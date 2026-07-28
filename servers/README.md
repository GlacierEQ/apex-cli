# APEX Servers

| Service | Module | Port | Purpose |
|---------|--------|------|---------|
| **Synthesizer** | `servers.synthesizer.main:app` | **8000** | Janus V2 neural link — Microwave ↔ Steward |

Legal/compliance Aspen Grove servers (`legal_core:8001`, `compliance_monitor:8002`) live in `GlacierEQ/aspen-grove-operator-v7` and are not duplicated here.

## Run Synthesizer

```bash
cd /path/to/apex-cli
export PYTHONPATH=$PWD
# use a venv that has fastapi + uvicorn
uvicorn servers.synthesizer.main:app --host 0.0.0.0 --port 8000
```

Or:

```bash
./apex-neural-link --maximize
```

Durable state: `~/.apex/neural_link/`
