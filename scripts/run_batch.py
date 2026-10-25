"""Run all conditions, retaining raw logs privately and recording source hashes."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[1]
TARGET = "openrouter/z-ai/glm-5.3"
OBSERVER = "openrouter/deepseek/deepseek-v4.1-flash"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", help="Unique output folder, e.g. batch-01")
    args = parser.parse_args()
    if Path(args.batch).name != args.batch or args.batch in (".", ".."):
        parser.error("batch must be a simple directory name")
    folder = ROOT / "logs" / args.batch
    folder.mkdir(parents=True, exist_ok=False)
    load_dotenv(ROOT / ".env")
    files = sorted(
        [
            *ROOT.glob("seeds/*/*.md"),
            *ROOT.glob("src/harbor_lab/*.py"),
            *ROOT.glob("scripts/*.py"),
            ROOT / "uv.lock",
            ROOT / "pyproject.toml",
        ]
    )
    manifest = {
        "started_utc": datetime.now(UTC).isoformat(),
        "target": TARGET,
        "auditor": OBSERVER,
        "judge": OBSERVER,
        "repeats": 3,
        "max_turns": 20,
        "epochs": 1,
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
        },
        "commands": [],
    }
    processes = []
    for variant in "ABC":
        command = [
            sys.executable,
            "-m",
            "inspect_ai",
            "eval",
            "src/harbor_lab/task.py@freight_audit",
            "-T",
            f"variant={variant}",
            "-T",
            "repeats=3",
            "-T",
            "max_turns=20",
            "--model",
            TARGET,
            "--log-dir",
            str(folder.relative_to(ROOT)),
        ]
        manifest["commands"].append(command[3:])
        output = (folder / f"run-{variant}.txt").open("w")
        processes.append(
            (subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT), output)
        )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    codes = []
    for process, output in processes:
        codes.append(process.wait())
        output.close()
    manifest["finished_utc"] = datetime.now(UTC).isoformat()
    manifest["exit_codes"] = codes
    manifest["logs"] = []
    for path in sorted(folder.glob("*.eval")):
        log = read_eval_log(path, header_only=True)
        manifest["logs"].append(
            {
                "file": path.name,
                "status": log.status,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"batch": args.batch, "exit_codes": codes, "logs": manifest["logs"]}))
    if (
        any(codes)
        or len(manifest["logs"]) != 3
        or any(log["status"] != "success" for log in manifest["logs"])
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
