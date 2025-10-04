import os
import sys
import subprocess
from pathlib import Path
import re
import time

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
    if len(sys.argv) == 4:
        count = int(sys.argv[1])
        exp_duration = int(sys.argv[2])
        lamda = sys.argv[3]
        
        base_logs = Path("./logs")
        exp_dir, exp_str = get_next_experiment_dir(base_logs)
        
        CONTROL_FILE = Path("control/run.flag")
        CONTROL_FILE.parent.mkdir(exist_ok=True)
        CONTROL_FILE.write_text("1")

        for i in range(count):
            log_dir = exp_dir / str(i)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            env = os.environ.copy()
            env["ID"] = str(i)
            env["EXP_STR"] = exp_str
            env["LOG_DIR"] = str(log_dir.resolve())
            env["LAMDA"] = lamda
            args = [
                "docker", "compose", "-f",
                "docker-compose.player.yaml", "-p",
                f"istream_player_{i}", "up", "-d",
                "--no-build", "--no-recreate", "--remove-orphans"]
            subprocess.run(args, env=env)
        
        try:
            print(f"Starting experiment: {exp_duration}s")
            time.sleep(exp_duration)
        
        finally:
            CONTROL_FILE.write_text("0")
            for i in range(count):
                project_name = f"istream_player_{i}"
                args = [
                    "docker", "compose",
                    "-f", "docker-compose.player.yaml",
                    "-p", project_name,
                    "down", "--remove-orphans"]
                print(f"Closing {project_name}")
                subprocess.run(args)
    else:
        print(sys.argv)
        exit(1)
    
 
if __name__ == "__main__":
    main()