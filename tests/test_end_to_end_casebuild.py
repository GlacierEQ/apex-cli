import os
import sys
import json
import hashlib
from pathlib import Path

# Setup paths
CB_ROOT = Path("/data/data/com.termux/files/home/MISSIONS/PRO_AGENTS/Casebuilder4000")
RED_ROOT = Path("/data/data/com.termux/files/home/MISSIONS/PRO_AGENTS/REPO_1001_RED_HELIX")

sys.path.append(str(CB_ROOT))
sys.path.append(str(CB_ROOT / ".cortex"))
sys.path.append(str(RED_ROOT))

from case_forge import CaseForge
from exhibit_hasher import ExhibitHasher
from adversarial_forge import AdversarialForge

def run_end_to_end():
    print("🚀 Starting End-to-End Casebuilding execution...")
    
    # Step 1: Create dummy binary exhibit
    exhibit_name = "exhibit_witness_statement.pdf"
    exhibit_path = CB_ROOT / "exhibits_binary" / exhibit_name
    exhibit_content = b"This is verified witness testimony for case 1010."
    exhibit_path.write_bytes(exhibit_content)
    print(f"[+] Created physical exhibit: {exhibit_name}")
    
    # Step 2: Seal the physical exhibit and generate sidecar
    hasher = ExhibitHasher(str(CB_ROOT / "exhibits_binary"))
    exhibit_hash = hasher.generate_hash_sidecar(exhibit_name)
    print(f"[+] Generated sidecar hash: {exhibit_hash}")
    
    # Step 3: Compile finalized payload
    payload = {
        "is_finalized": True,
        "evidence": [exhibit_name],
        "analysis": "Testimony verifies actor was present. Clear anomalies detected in transaction logs."
    }
    
    # Step 4: Seal case and append to custody ledger
    forge = CaseForge(str(CB_ROOT))
    sealed_case_path = forge.build_case("CASE_1010_ALPHA", payload)
    print(f"[+] Case successfully forged and sealed at: {sealed_case_path}")
    
    # Step 5: subject the case to Red Helix adversarial forge
    adversary = AdversarialForge(str(RED_ROOT))
    red_report = adversary.attack_case(sealed_case_path)
    print(f"[+] Red Team opposing counsel report created: {red_report}")
    
    # Print ledger entries
    ledger_path = CB_ROOT / "chain_of_custody" / "CASE_1010_ALPHA_custody.jsonl"
    print("\n📜 Chain of Custody ledger entries:")
    print(ledger_path.read_text())

if __name__ == "__main__":
    run_end_to_end()
