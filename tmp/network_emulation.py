#!/usr/bin/env python3
import yaml
import os
import subprocess
from pathlib import Path
import re
import time
import argparse
import random
import sys

control_file = Path("control/run.flag")

# ---------- helpers ----------

def get_next_experiment_dir(base: Path) -> Path:
    base.mkdir(exist_ok=True)
    max_idx = -1
    pattern = re.compile(r"^experiment_(\d+)$")

    for d in base.iterdir():
        if d.is_dir():
            m = pattern.match(d.name)
            if m:
                idx = int(m.group(1))
                max_idx = max(max_idx, idx)

    next_idx = max_idx + 1
    new_dir = base / f"experiment_{next_idx}"
    new_dir.mkdir(exist_ok=True)
    return new_dir, f"experiment_{next_idx}"


def wait_for_container_startup(prefixes):
    while True:
        result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                                capture_output=True, text=True)
        running = result.stdout.strip().splitlines()
        if all(any(name.startswith(prefix) for name in running) for prefix in prefixes):
            return
        time.sleep(0.2)


def apply_netem(container_name: str, rate: str, delay: str, loss: str = "0%"):
    """Apply network emulation using tc inside container"""
    cmd = [
        "docker", "exec", container_name, "tc", "qdisc", "replace", "dev", "eth0",
        "root", "handle", "1:", "tbf", "rate", rate, "burst", "32kbit", "latency", "400ms"
    ]
    subprocess.run(cmd, capture_output=True)

    if delay != "0ms" or loss != "0%":
        cmd2 = [
            "docker", "exec", container_name, "tc", "qdisc", "add", "dev", "eth0",
            "parent", "1:", "handle", "10:", "netem",
            "delay", delay, "loss", loss
        ]
        subprocess.run(cmd2, capture_output=True)


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help='Path to the yaml config')
    args = parser.parse_args()

    config_path = args.config
    with open(config_path) as stream:
        config = yaml.safe_load(stream)

    count = config["n_containers"]
    exp_duration = config["duration"]
    lamda = config["sleep_lambda"]
    node_id = config["node_id"]
    istream_player_config_path = config["istream_player_config_path"]

    # network emulation config
    net_profile = config.get("network_profile", {})
    default_rate = net_profile.get("rate", "5mbit")
    default_delay = net_profile.get("delay", "50ms")
    default_loss = net_profile.get("loss", "0%")
    randomize = net_profile.get("randomize", False)

    base_logs = Path("./logs")
    exp_dir, exp_str = get_next_experiment_dir(base_logs)

    # set control flag
    control_file.parent.mkdir(exist_ok=True)
    control_file.write_text("1")

    for i in range(count):
        log_dir = exp_dir / str(i)
        log_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update({
            "ID": str(i),
            "EXP_STR": exp_str,
            "LOG_DIR": str(log_dir.resolve()),
            "LAMDA": str(lamda),
            "NODE_ID": str(node_id),
            "ISTREAM_CONFIG": str(istream_player_config_path)
        })

        docker_args = [
            "docker", "compose", "-f",
            "docker-compose.player.yaml", "-p",
            f"istream_player_{i}", "up", "-d",
            "--no-build", "--no-recreate", "--remove-orphans"
        ]
        subprocess.run(docker_args, env=env, check=True)

    prefixes = [f"istream_player_{i}" for i in range(count)]
    wait_for_container_startup(prefixes)

    print("Applying network emulation settings...")

    for i, prefix in enumerate(prefixes):
        # fetch container name (actual runtime name)
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={prefix}", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        container_name = result.stdout.strip()

        if not container_name:
            print(f"[WARN] Container {prefix} not found")
            continue

        # random variation if enabled
        rate = default_rate
        delay = default_delay
        loss = default_loss
        if randomize:
            # ±20% bandwidth, ±30ms delay, ±0.5% loss
            bw_val = int(re.match(r"(\d+)", default_rate).group(1))
            rate = f"{int(bw_val * random.uniform(0.8, 1.2))}mbit"
            delay_ms = int(re.match(r"(\d+)", default_delay).group(1))
            delay = f"{max(0, int(delay_ms + random.uniform(-30, 30)))}ms"
            loss = f"{max(0, float(default_loss.strip('%')) + random.uniform(-0.5, 0.5)):.2f}%"

        apply_netem(container_name, rate, delay, loss)
        print(f"  {container_name}: rate={rate}, delay={delay}, loss={loss}")

    print(f"Experiment running for {exp_duration}s")
    try:
        time.sleep(exp_duration)
    finally:
        control_file.write_text("0")

        for i in range(count):
            project_name = f"istream_player_{i}"
            print(f"Stopping {project_name}")
            subprocess.run([
                "docker", "compose",
                "-f", "docker-compose.player.yaml",
                "-p", project_name,
                "down", "--remove-orphans"
            ], check=False)

        print("Cleaning up tc rules...")
        for prefix in prefixes:
            subprocess.run(["docker", "exec", prefix, "tc", "qdisc", "del", "dev", "eth0", "root"],
                           stderr=subprocess.DEVNULL)

        print("Experiment finished.")


if __name__ == "__main__":
    main()
