import os
import sys
import subprocess
from pathlib import Path
import re
import time
import argparse

csv_bandwidth_dir = "../5G-production-dataset/5G-production-dataset/Download/Static/"
control_file = Path("control/run.flag")

# create folder for experiment
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

# wait until all containers are online
def wait_for_container_startup(prefixes):
    while True:
        result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],capture_output=True, text=True)
        running = result.stdout.strip().splitlines()
        if all(any(name.startswith(prefix) for name in running) for prefix in prefixes):
                return
        time.sleep(0.1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, required=True, help='number of containers')
    parser.add_argument('--exp-duration', type=int, required=True, help='experiment duration in seconds')
    parser.add_argument('--lamda', type=str, required=True, help='lambda parameter for exponential distribution')
    parser.add_argument('--csv-file', type=Path, default=None, help='csv files for bandwidth control')
    parser.add_argument('--bandwidth', type=int, default=None, help='static bandwidth value in kbit/s')
    
    args = parser.parse_args()
    
    count = args.count
    exp_duration = args.exp_duration
    lamda = args.lamda
        
    base_logs = Path("./logs")
    exp_dir, exp_str = get_next_experiment_dir(base_logs)
        
    # set control flag
    control_file.parent.mkdir(exist_ok=True)
    control_file.write_text("1")
        
    if args.csv_file:
        csv_bandwidth_list = [str(args.csv_file)]
    else:
        csv_bandwidth_list = [str(p) for p in Path(csv_bandwidth_dir).iterdir() if p.is_file()]
                    
    for i in range(count):
        log_dir = exp_dir / str(i)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # variables for container
        env = os.environ.copy()
        env["ID"] = str(i)
        env["EXP_STR"] = exp_str
        env["LOG_DIR"] = str(log_dir.resolve())
        env["LAMDA"] = lamda
        
        # start container
        docker_args = [
            "docker", "compose", "-f",
            "docker-compose.player.yaml", "-p",
            f"istream_player_{i}", "up", "-d",
            "--no-build", "--no-recreate", "--remove-orphans"]
        subprocess.run(docker_args, env=env)

    prefixes = [f"istream_player_{i}" for i in range(count)]
    wait_for_container_startup(prefixes)
    
    if args.bandwidth:
        tc_proc = subprocess.Popen([
            "python3", "tc_bandwidth_control.py", 
            "--count", str(count), 
            "--bandwidth", str(args.bandwidth)
        ])
    else:
        tc_proc = subprocess.Popen([
            "python3", "tc_bandwidth_control.py", 
            "--count", str(count), 
            "--csv-files"] + csv_bandwidth_list
        )
    try:
        # start timer
        print(f"starting experiment: {exp_duration}s")
        time.sleep(exp_duration)

    finally:
        # reset control flag
        control_file.write_text("0")

        # stop container
        for i in range(count):
            project_name = f"istream_player_{i}"
            docker_args = [
                "docker", "compose",
                "-f", "docker-compose.player.yaml",
                "-p", project_name,
                "down", "--remove-orphans"]
            print(f"Closing {project_name}")
            subprocess.run(docker_args)
            
        # stop bandwidth skript    
        tc_proc.terminate()
        tc_proc.wait()
 
if __name__ == "__main__":
    main()