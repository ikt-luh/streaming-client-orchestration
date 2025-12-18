import yaml
import os
import subprocess
from pathlib import Path
import re
import time
import argparse


CONTROL_FILE = Path("control/run.flag")


def get_next_experiment_dir(base: Path):
    """Create and return the next numbered experiment directory."""
    base.mkdir(exist_ok=True)
    pattern = re.compile(r"^experiment_(\d+)$")
    max_idx = -1

    for d in base.iterdir():
        if d.is_dir():
            m = pattern.match(d.name)
            if m:
                max_idx = max(max_idx, int(m.group(1)))

    next_idx = max_idx + 1
    new_dir = base / f"experiment_{next_idx}"
    new_dir.mkdir(exist_ok=True)
    return new_dir, f"experiment_{next_idx}"


def wait_for_container_startup(prefixes, timeout=60):
    """Wait until all containers with given prefixes are running."""
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        running = result.stdout.strip().splitlines()
        if all(any(name.startswith(prefix) for name in running) for prefix in prefixes):
            print("[ok] All containers online.")
            return
        time.sleep(0.2)
    raise TimeoutError("Some containers failed to start in time.")


def main():
    parser = argparse.ArgumentParser(description="Experiment orchestration script")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    config_path = args.config
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # === Extract config ===
    n_containers = cfg["n_containers"]
    exp_duration = cfg["duration"]
    lamda = cfg["sleep_lambda"]
    node_id = cfg.get("node_id", 0)
    istream_config = cfg["istream_player_config_path"]
    bw_min = cfg.get("bandwidth_min", 500)
    bw_max = cfg.get("bandwidth_max", 5000)

    # === Prepare directories ===
    base_logs = Path("./logs")
    exp_dir, exp_name = get_next_experiment_dir(base_logs)
    CONTROL_FILE.parent.mkdir(exist_ok=True)
    CONTROL_FILE.write_text("1")

    print(f"Starting experiment: {exp_name}")
    print(f"  containers : {n_containers}")
    print(f"  duration   : {exp_duration}s")
    print(f"  lambda     : {lamda}")
    print(f"  node_id    : {node_id}")
    print(f"  config     : {istream_config}")
    print(f"  bw range   : {bw_min}–{bw_max} kbps")

    # === Start containers ===
    for i in range(n_containers):
        log_dir = exp_dir / str(i)
        log_dir.mkdir(parents=True, exist_ok=True)
        trace_id = i

        env = os.environ.copy()
        env.update({
            "ID": str(i),
            "EXP_STR": exp_name,
            "LOG_DIR": str(log_dir.resolve()),
            "LAMDA": str(lamda),
            "NODE_ID": str(node_id),
            "ISTREAM_CONFIG": str(istream_config),
            "TRACE_ID": str(trace_id),
            "EXPERIMENT_CONFIG": str(config_path),
        })

        cmd = [
            "docker", "compose",
            "-f", "docker-compose.yaml",
            "-p", f"istream_player_{i}",
            "up", "-d", "--build", "--remove-orphans"
        ]
        subprocess.run(cmd, env=env, check=True)
        print(cmd)

    prefixes = [f"istream_player_{i}" for i in range(n_containers)]
    wait_for_container_startup(prefixes)

    # === Run experiment ===
    print(f"Experiment running for {exp_duration}s")
    try:
        time.sleep(exp_duration)
    finally:
        # === Stop experiment ===
        CONTROL_FILE.write_text("0")
        print("\nStopping all containers...")

        for i in range(n_containers):
            project = f"istream_player_{i}"
            subprocess.run([
                "docker", "compose",
                "-f", "docker-compose.player.yaml",
                "-p", project,
                "down", "--remove-orphans"
            ])
            print(f"[ok] {project} stopped.")

        print("All containers stopped. Experiment complete.")


if __name__ == "__main__":
    main()
