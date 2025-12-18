import numpy as np
import glob
import os

INPUT_DIR = "resources/traces"
OUTPUT_DIR = "resources/traces"
MIN_KBIT = 50.0

os.makedirs(OUTPUT_DIR, exist_ok=True)

trace_idx = 0

for path in sorted(glob.glob(os.path.join(INPUT_DIR, "*.log"))):
    out_path = os.path.join(OUTPUT_DIR, f"trace_{trace_idx}.csv")

    with open(path, "r") as fin, open(out_path, "w") as fout:
        fout.write("timestamp_ms,bandwidth_kbit_s\n")
        bws = []

        for line in fin:
            if not line.strip():
                continue

            cols = line.split()
            if len(cols) < 6:
                continue

            timestamp_ms = int(cols[0])
            bytes_tx = float(cols[4])
            duration_ms = float(cols[5])

            if duration_ms <= 0:
                continue

            kbit_per_s = (bytes_tx * 8.0) / duration_ms
            bws.append(kbit_per_s)

            if kbit_per_s >= MIN_KBIT:
                fout.write(f"{timestamp_ms},{kbit_per_s:.3f}\n")
            
    print("Trace {}, avg {} kbit/s, duration: {}s".format(
        trace_idx, np.mean(bws), len(bws)
    ))

    trace_idx += 1
