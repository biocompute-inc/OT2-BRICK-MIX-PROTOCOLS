import time
import requests
import sys
import platform

# =======================
# CONFIG
# =======================

# OT-2 address
ROBOT_HOST = "169.254.51.252"
ROBOT_PORT = 31950

# How often to poll the robot (seconds)
POLL_INTERVAL_SEC = 5

# Required header for OT-2 HTTP API v2
HEADERS = {
    "Opentrons-Version": "2",
}


# =======================
# SOUND HELPER
# =======================

def play_sound():
    """
    Make some noise when the OT-2 run is paused.
    On Windows: use winsound. On others: terminal bell.
    """
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            # This may beep in many terminals
            sys.stdout.write("\a")
            sys.stdout.flush()
        print("[watcher] BEEP! OT-2 run paused.")
    except Exception as e:
        print("[watcher] Could not play sound:", e)


# =======================
# OT-2 RUN POLLING
# =======================

def get_latest_run():
    """
    Query the OT-2 HTTP API for the list of runs and return the latest one (if any).

    Endpoint: GET /runs  with header Opentrons-Version: 2
    """
    url = f"http://{ROBOT_HOST}:{ROBOT_PORT}/runs"
    resp = requests.get(url, headers=HEADERS, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    runs = data.get("data", [])
    if not runs:
        return None

    # Most recent by createdAt
    runs_sorted = sorted(
        runs,
        key=lambda r: r.get("createdAt", ""),
        reverse=True,
    )
    return runs_sorted[0]


def main():
    print(f"[watcher] Watching OT-2 at {ROBOT_HOST}:{ROBOT_PORT}")
    print(f"[watcher] Poll interval: {POLL_INTERVAL_SEC}s")

    last_status = None
    last_run_id = None

    try:
        while True:
            try:
                latest = get_latest_run()
                if latest is None:
                    print("[watcher] No runs found yet.")
                    time.sleep(POLL_INTERVAL_SEC)
                    continue

                run_id = latest.get("id")
                status = latest.get("status")

                if run_id != last_run_id:
                    print(f"[watcher] New run detected: {run_id} (status={status})")
                    last_run_id = run_id
                    last_status = status

                if status != last_status:
                    print(f"[watcher] Run {run_id} status changed: {last_status} -> {status}")
                    last_status = status

                    if status == "paused":
                        msg = "OT-2 run paused – check Opentrons App for instructions."
                        print("[watcher]", msg)
                        play_sound()

                time.sleep(POLL_INTERVAL_SEC)

            except requests.HTTPError as e:
                print("[watcher] HTTP error:", e)
                time.sleep(POLL_INTERVAL_SEC)
            except Exception as e:
                print("[watcher] Error:", e)
                time.sleep(POLL_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\n[watcher] Stopped by user (Ctrl+C).")


if __name__ == "__main__":
    main()
