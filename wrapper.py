import sys
import os
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any
from istream_player.config.config import PlayerConfig
from istream_player.core.module_composer import PlayerComposer
from istream_player.main import load_from_dict, load_from_config_file
import asyncio
import logging
import random
import time
import json

TC_BIN = "/sbin/tc"


container_id = os.environ.get("ID", "")
container_exp = os.environ.get("EXP_STR", "")
lamda = os.environ.get("LAMDA", "")
control_file = Path(os.getenv("CONTROL_FILE", "/app/control/run.flag"))
ready_file = Path("control/ready.flag")
node_id = os.environ.get("NODE_ID", "")
config_path = os.environ.get("ISTREAM_CONFIG", ".ressources/online.yaml")

class Wrapper:
    def __init__(self):
        self.config_dir = Path(__file__).parent / "resources"
        self.node_logged = False
        self.bw_min = int(os.getenv("BANDWIDTH_MIN", "500"))     # kbps
        self.bw_max = int(os.getenv("BANDWIDTH_MAX", "5000"))    # kbps
        random.seed(f"{container_id}{node_id}")

    def generate_bandwidth(self) -> int:
        """Draw random bandwidth in kbps for this session"""
        return random.randint(self.bw_min, self.bw_max)
    
    def load_env_overrides(self) -> Dict[str, Any]:
        """Load configuration overrides from environment variables"""
        env_config = {}

        env_mappings = {
            "ISTREAM_INPUT": "input",
            "ISTREAM_RUN_DIR": "run_dir",
            "ISTREAM_TIME_FACTOR": "time_factor",
            "ISTREAM_DOWNLOADER": "mod_downloader",
            "ISTREAM_BW": "mod_bw",
            "ISTREAM_ABR": "mod_abr",
            "ISTREAM_SCHEDULER": "mod_scheduler",
            "ISTREAM_BUFFER": "mod_buffer",
            "ISTREAM_PLAYER": "mod_player",
            "ISTREAM_VERBOSE": "verbose",
            "ISTREAM_BUFFER_DURATION": "buffer_duration",
            "ISTREAM_SAFE_BUFFER_LEVEL": "safe_buffer_level",
            "ISTREAM_PANIC_BUFFER_LEVEL": "panic_buffer_level",
            "ISTREAM_MIN_REBUFFER_DURATION": "min_rebuffer_duration",
            "ISTREAM_MIN_START_DURATION": "min_start_duration",
        }

        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if config_key == "verbose":
                    env_config[config_key] = value.lower() in ["true", "1", "yes", "on"]
                elif config_key in [
                    "time_factor",
                    "buffer_duration",
                    "safe_buffer_level",
                    "panic_buffer_level",
                    "min_rebuffer_duration",
                    "min_start_duration",
                ]:
                    env_config[config_key] = float(value)
                elif config_key.startswith("mod_analyzer") and "," in value:
                    env_config[config_key] = [
                        analyzer.strip() for analyzer in value.split(",")
                    ]
                else:
                    env_config[config_key] = value

        return env_config

    # draw random value for sleep time duration between sessions
    def generate_sleep_time(self) -> float:
            return random.expovariate(float(lamda))
        
    def run_with_config_file(self, config_file: str, overrides: Dict[str, Any] = None):
        composer = PlayerComposer()
        composer.register_core_modules()
        config = PlayerConfig()

        load_from_config_file(config_file, config)
        env_overrides = self.load_env_overrides()

        if container_id != "" and container_exp != "":
            base_run_dir = env_overrides.get("run_dir", getattr(config, "run_dir", "./logs"))
            env_overrides["run_dir"] = os.path.join(base_run_dir, container_exp, container_id)

        # pick bandwidth and sleep time for this session
        sleep_time = self.generate_sleep_time()
        bandwidth_kbps = self.generate_bandwidth()

        # apply bandwidth limit locally
        set_bandwidth_limit(bandwidth_kbps)

        if env_overrides:
            load_from_dict(env_overrides, config)
        if overrides:
            load_from_dict(overrides, config)

        config.validate()
        verbose = getattr(config, "verbose", False)
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format="%(asctime)s %(name)20s %(levelname)8s:\t%(message)s",
        )

        # wait for readiness flag
        while True:
            if ready_file.exists() and ready_file.read_text().strip() == "1":
                break
            time.sleep(0.1)

        # log metadata including bandwidth
        if not self.node_logged and node_id:
            log_session(env_overrides["run_dir"], node_id=node_id)
            self.node_logged = True
        log_session(env_overrides["run_dir"], time.time(), sleep_time, bandwidth_kbps)

        time.sleep(sleep_time)
        asyncio.run(composer.run(config))


# log extra info of session
def log_session(path: str, timestamp: float = None, sleep_duration: float = None,
                bandwidth_kbps: int = None, node_id: str = None):
    filepath = os.path.join(path, "info.json")
    os.makedirs(path, exist_ok=True)

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"node_id": node_id, "sessions": []}

    if node_id and "node_id" not in data:
        data["node_id"] = node_id
    elif timestamp is not None and sleep_duration is not None:
        entry = {"timestamp": timestamp, "sleep_duration": sleep_duration}
        if bandwidth_kbps is not None:
            entry["bandwidth_kbps"] = bandwidth_kbps
        data.setdefault("sessions", []).append(entry)

    with open(filepath, "w") as f:
        json.dump(data, f)



def set_bandwidth_limit(bandwidth_kbps: int):
    """
    Apply bandwidth limit (in kbps) using Linux tc in the container.
    Assumes 'eth0' as the active interface.
    """
    iface = "eth0"
    ifb = "ifb0"
    rate = f"{bandwidth_kbps}kbit"

    try:
                # clean existing
        subprocess.run([TC_BIN, "qdisc", "del", "dev", iface, "root"], stderr=subprocess.DEVNULL)
        subprocess.run([TC_BIN, "qdisc", "del", "dev", ifb, "root"], stderr=subprocess.DEVNULL)
        subprocess.run(["ip", "link", "set", ifb, "down"], stderr=subprocess.DEVNULL)

        # setup ifb
        subprocess.run(["modprobe", "ifb", "numifbs=1"], check=False)
        subprocess.run(["ip", "link", "set", "dev", ifb, "up"], check=True)
        subprocess.run([TC_BIN, "qdisc", "add", "dev", iface, "handle", "ffff:", "ingress"], check=True)
        subprocess.run([
            TC_BIN, "filter", "add", "dev", iface, "parent", "ffff:", "protocol", "ip",
            "u32", "match", "u32", "0", "0", "action", "mirred", "egress", "redirect", "dev", ifb
        ], check=True)

        # apply both
        subprocess.run([
            TC_BIN, "qdisc", "add", "dev", iface, "root", "tbf",
            "rate", rate, "burst", "32kbit", "latency", "400ms"
        ], check=True)
        subprocess.run([
            TC_BIN, "qdisc", "add", "dev", ifb, "root", "tbf",
            "rate", rate, "burst", "32kbit", "latency", "400ms"
        ], check=True)

        print(f"[bandwidth] Set limit {rate} on {iface} (egress) and {ifb} (ingress)")
    except subprocess.CalledProcessError as e:
        print(f"[bandwidth] Failed to set limit: {e}")


def main():
    wrapper = Wrapper()
    
    # Loop for running multiple streaming sessions in one experiment
    while True: 
        # Check if the experiment is still active
        if not control_file.exists() or control_file.read_text().strip() != "1":
            print("stop container loop")
            break
        
        # Run new streaming session
        wrapper.run_with_config_file(config_path)


if __name__ == "__main__":
    main()
