import os
import sys
import subprocess
from pathlib import Path
import re

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

def main():
    if len(sys.argv) == 2:
        count = int(sys.argv[1])
        
        base_logs = Path("./logs")
        exp_dir, exp_str = get_next_experiment_dir(base_logs)
        
        for i in range(count):
            log_dir = Path("./logs") / str(i)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            env = os.environ.copy()
            env["ID"] = str(i)
            env["EXP_STR"] = exp_str
            env["LOG_DIR"] = str(log_dir.resolve())
            args = [
                "docker", "compose", "-f",
                "docker-compose.player.yaml", "-p",
                f"istream_player_{i}", "up", "-d",
                "--no-build", "--no-recreate", "--remove-orphans"]
            subprocess.run(args, env=env)
    else:
        print(sys.argv)
        exit(1)
    
 
if __name__ == "__main__":
    main()