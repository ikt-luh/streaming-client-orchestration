import sys
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from istream_player.config.config import PlayerConfig
from istream_player.core.module_composer import PlayerComposer
from istream_player.main import load_from_dict, load_from_config_file
import asyncio
import logging
import random
import time

container_id = os.environ.get("ID", "")
container_exp = os.environ.get("EXP_STR", "")
lamda = os.environ.get("LAMDA", "")
active_file = Path(f"control/active_{container_id}.flag")
control_file = Path(os.getenv("CONTROL_FILE", "/app/control/run.flag"))
ready_file = Path("control/ready.flag")  

class Wrapper:
    def __init__(self):
        self.config_dir = Path(__file__).parent / "resources"
        self.config_dir.mkdir(exist_ok=True)
        self.create_default_configs()
        self.random = random.seed(container_id)
        

    def create_default_configs(self):
        default_config = {
            "input": "http://localhost:8000/output.mpd",
            "run_dir": "./logs",
            "time_factor": 1.0,
            "mod_downloader": "tcp",
            "mod_bw": "bw_meter",
            "mod_abr": "dash",
            "mod_scheduler": "scheduler",
            "mod_buffer": "buffer_manager",
            "mod_analyzer": ["data_collector"],
            "verbose": True,
            "buffer_duration": 8.0,
            "safe_buffer_level": 6.0,
            "panic_buffer_level": 2.5,
            "min_rebuffer_duration": 2.0,
            "min_start_duration": 2.0,
        }

        configs = {"default.yaml": default_config}

        for filename, config in configs.items():
            config_path = self.config_dir / filename
            if not config_path.exists():
                with open(config_path, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)

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

    def run_with_config_name(self, config_name: str, overrides: Dict[str, Any] = None):
        config_file = self.config_dir / f"{config_name}.yaml"
        self.run_with_config_file(str(config_file), overrides)

    # draw random value for sleep time duration between sessions
    def generate_start_time(self) -> float:
            return random.expovariate(float(lamda))
        
    def run_with_config_file(self, config_file: str, overrides: Dict[str, Any] = None):
        
        composer = PlayerComposer()
        composer.register_core_modules()
        config = PlayerConfig()

        print(f"loading configuration from: {config_file}")
        load_from_config_file(config_file, config)

        env_overrides = self.load_env_overrides()
        
        if container_id != "" and container_exp != "":
            base_run_dir = env_overrides.get("run_dir", getattr(config, "run_dir", "./logs"))
            env_overrides["run_dir"] = os.path.join(base_run_dir, container_exp, container_id)
            
        start_time = self.generate_start_time()
    
        if env_overrides:
            print(f"applying environment overrides: {list(env_overrides.keys())}")
            load_from_dict(env_overrides, config)

        if overrides:
            print(f"applying command line overrides: {list(overrides.keys())}")
            load_from_dict(overrides, config)

        verbose = getattr(config, "verbose", False)
        if verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(name)20s %(levelname)8s:\t%(message)s",
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s %(name)20s %(levelname)8s:\t%(message)s",
            )
        config.validate()
        print(f"starting player with input: {getattr(config, 'input', 'N/A')}")
        
        # mark container as active
        active_file.parent.mkdir(exist_ok=True)
        active_file.write_text("1")
        
        # wait for tc bandwidth control skript to signal readiness
        while True:
            if ready_file.exists() and ready_file.read_text().strip() == "1":
                print("waiting for ready flag")
                break
            time.sleep(0.1)
    
        time.sleep(start_time) # wait for random the random time
        asyncio.run(composer.run(config)) # run session


def parse_overrides(args):
    overrides = {}

    for arg in args:
        if arg.startswith("--") and "=" in arg:
            key, value = arg[2:].split("=", 1)

            if value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            elif value.replace(".", "").replace("-", "").isdigit():
                value = float(value) if "." in value else int(value)

            overrides[key] = value

    return overrides


def main():
    wrapper = Wrapper()

    if len(sys.argv) < 2:
        # default behavior
        wrapper.run_with_config_name("default")
        return

    first_arg = sys.argv[1]
    config_name = first_arg
    overrides = parse_overrides(sys.argv[2:])
    
    while True: 
        
        # stop restarting the session
        if not control_file.exists() or control_file.read_text().strip() != "1":
            print("stop container loop")
            
            active_file.parent.mkdir(exist_ok=True)
            active_file.write_text("0")
            break
        
        wrapper.run_with_config_name(config_name, overrides)


if __name__ == "__main__":
    main()
