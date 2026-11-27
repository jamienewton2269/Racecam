#!/usr/bin/env python3
"""RaceCam start timing model; simulation only, not Android acoustic validation."""
import argparse
import json
import statistics

def evaluate(samples, tolerance_ms=2000):
    if len(samples) < 2:
        raise ValueError("At least two devices are required")
    ids = [s["device"] for s in samples]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate device")
    for s in samples:
        if not isinstance(s["gun_onset_utc_ms"], (int, float)):
            raise ValueError("Missing gun onset")
        if not isinstance(s["target_utc_ms"], (int, float)):
            raise ValueError("Missing start target")
    targets = {s["target_utc_ms"] for s in samples}
    if len(targets) != 1:
        raise ValueError("Different scheduled starts")
    target = targets.pop()
    offsets = [s["gun_onset_utc_ms"]-target for s in samples]
    spread = max(offsets)-min(offsets)
    return {"devices":len(samples),"spread_ms":round(spread,3),
            "earliest_error_ms":round(min(offsets),3),
            "latest_error_ms":round(max(offsets),3),
            "mean_error_ms":round(statistics.mean(offsets),3),
            "within_2s":spread<=tolerance_ms,
            "measurement":"supplied onset timestamps; acoustic validation required"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",help="JSON array of device, target_utc_ms, gun_onset_utc_ms")
    args=parser.parse_args()
    if args.input:
        with open(args.input,encoding="utf-8") as f: samples=json.load(f)
    else:
        samples=[{"device":f"sim-{i}","target_utc_ms":100000,"gun_onset_utc_ms":100000+d}
                 for i,d in enumerate([120,310,510])]
    print(json.dumps(evaluate(samples),indent=2))
if __name__=="__main__":main()
