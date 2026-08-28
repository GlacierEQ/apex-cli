#!/usr/bin/env python3
"""
apex_node.py — APEX Local Edge Node
Forensic evidence intake pipeline with MCP server.
Drop files into apex_intake_buffer/ → OCR → SHA-256 → apex_permanent_substrate/
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import pdfplumber
    import pytesseract
    from pdf2image import convert_from_path

    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print(
        "WARNING: OCR dependencies not installed. Run: uv pip install pdfplumber pytesseract pdf2image"
    )

try:
    from mcp.server.fastmcp import FastMCP

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("WARNING: MCP not installed. Run: uv pip install mcp")

# ==========================================
# APEX SYSTEM CONFIGURATION
# ==========================================
CASE_NUMBER = "1FDV-23-0001009"
BUFFER_DIR = Path("./apex_intake_buffer")
SUBSTRATE_DIR = Path("./apex_permanent_substrate")

BUFFER_DIR.mkdir(parents=True, exist_ok=True)
SUBSTRATE_DIR.mkdir(parents=True, exist_ok=True)

if HAS_MCP:
    mcp = FastMCP("APEX_Forensic_Edge_Node")


# ==========================================
# EXTRACTION & METADATA FUNCTIONS
# ==========================================
def execute_forensic_extraction(file_path: Path) -> str:
    text_content = ""
    try:
        if file_path.suffix.lower() == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"

            if not text_content.strip() and HAS_OCR:
                images = convert_from_path(str(file_path))
                for image in images:
                    text_content += pytesseract.image_to_string(image) + "\n"
        else:
            # For images, use OCR directly
            if HAS_OCR:
                from PIL import Image

                img = Image.open(file_path)
                text_content = pytesseract.image_to_string(img)
    except Exception as e:
        return f"[ERROR: OCR PIPELINE FAILURE] {str(e)}"

    return text_content.strip()


def generate_manifest_payload(file_path: Path, extracted_text: str) -> tuple:
    date_str = datetime.now().strftime("%Y%m%d")
    file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    new_filename = (
        f"{CASE_NUMBER}_{date_str}_INT_v1_RawIntake_{file_hash[:8]}{file_path.suffix}"
    )

    payload = {
        "case_number": CASE_NUMBER,
        "evidence_title": new_filename,
        "event_date": datetime.now().isoformat(),
        "source_system": "Local_MCP_Edge_Node",
        "artifact_pointer": str(SUBSTRATE_DIR / new_filename),
        "sha256_checksum": file_hash,
        "extracted_content": extracted_text[:10000],
        "status": "L1_MANIFESTED",
    }

    return payload, new_filename


def process_binary_artifact(file_path: Path):
    extracted_text = execute_forensic_extraction(file_path)
    payload, new_filename = generate_manifest_payload(file_path, extracted_text)
    target_path = SUBSTRATE_DIR / new_filename
    shutil.move(str(file_path), str(target_path))
    manifest_path = target_path.with_suffix(".json")
    with open(manifest_path, "w") as f:
        json.dump(payload, f, indent=4)
    print(f"[INGESTED] {new_filename} → {target_path}")


# ==========================================
# WATCHDOG EVENT HANDLER
# ==========================================
class ApexForensicHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if file_path.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]:
            process_binary_artifact(file_path)


# ==========================================
# MCP TOOLS
# ==========================================
if HAS_MCP:

    @mcp.tool()
    def read_recent_manifests(limit: int = 5) -> list:
        manifests = []
        json_files = sorted(
            SUBSTRATE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True
        )
        for json_file in json_files[:limit]:
            with open(json_file, "r") as f:
                manifests.append(json.load(f))
        return manifests

    @mcp.tool()
    def force_intake_sweep() -> str:
        processed_count = 0
        for file_path in BUFFER_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in [
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
            ]:
                process_binary_artifact(file_path)
                processed_count += 1
        return f"[SUCCESS] Swept and manifested {processed_count} artifacts."

    @mcp.tool()
    def list_evidence() -> list:
        files = []
        for f in SUBSTRATE_DIR.iterdir():
            if f.suffix == ".json":
                with open(f) as fh:
                    data = json.load(fh)
                    files.append(
                        {
                            "filename": f.stem,
                            "sha256": data.get("sha256_checksum", "")[:16],
                            "status": data.get("status", ""),
                        }
                    )
        return files


# ==========================================
# RUNTIME EXECUTION
# ==========================================
def start_watchdog():
    observer = Observer()
    observer.schedule(ApexForensicHandler(), str(BUFFER_DIR), recursive=False)
    observer.start()
    return observer


if __name__ == "__main__":
    print(f"=== APEX Edge Node — Case {CASE_NUMBER} ===")
    print(f"Buffer: {BUFFER_DIR}")
    print(f"Substrate: {SUBSTRATE_DIR}")
    print(f"OCR: {'✅' if HAS_OCR else '❌'}")
    print(f"MCP: {'✅' if HAS_MCP else '❌'}")
    print()

    observer = start_watchdog()
    print("Watchdog started. Monitoring intake buffer...")

    if HAS_MCP:
        try:
            mcp.run()
        finally:
            observer.stop()
            observer.join()
    else:
        print("MCP not available — running in standalone mode")
        print("Drop files into apex_intake_buffer/ to process")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
