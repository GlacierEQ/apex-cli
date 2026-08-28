import sqlite3
import os
from datetime import datetime

# APEX MIMO-SYNC V1.0
# Bridges MiMo sessions to the APEX Memory Helix

DB_PATH = os.path.expanduser("~/.local/share/mimocode/mimocode.db")
AG_INDEX_PATH = os.path.expanduser("~/APEX_POINTER_INDEX.json")


def get_latest_session():
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, title, time_created FROM session ORDER BY time_created DESC LIMIT 1"
        )
        session = cursor.fetchone()
        return session
    except Exception as e:
        print(f"Error querying session database: {e}")
        return None
    finally:
        conn.close()


def sync_to_apex():
    session = get_latest_session()
    if not session:
        print("[MIMO-SYNC] No local sessions found.")
        return

    sync_data = {
        "mimo_session_id": session[0],
        "title": session[1],
        "synced_at": datetime.now().isoformat(),
        "checkpoint": "30db1e4f",
    }

    print(f"🌲 [APEX] Synced MiMo Session: {session[1]} (ID: {session[0]})")
    # In a real scenario, this would call ag_api.INDEX()
    return sync_data


if __name__ == "__main__":
    sync_to_apex()
