#!/usr/bin/env python3
"""Puts the monitored pipelines back in their failing state with a single push to main.

Run it with your own GitHub CLI session (`gh auth login`), not from a workflow: a push or dispatch
made with a workflow's GITHUB_TOKEN would not trigger the Pipesor report workflow.

    python3 scripts/demo_break.py                    # every case
    python3 scripts/demo_break.py staging release    # only these cases
    python3 scripts/demo_break.py --repo owner/repo  # another copy of the repository

Cases: deploy, tests, staging, release, reports. Files that are already broken get no change, so
their workflow is dispatched instead; either way each chosen pipeline runs once and fails.
"""

import argparse
import base64
import json
import subprocess
import sys

REPO = "Chaomeum/pipesor-demo"
BRANCH = "main"
# path -> (fixed text, failing text, workflow that the path triggers)
BREAKS = {
    "deploy/orders-api.env": (
        "HEALTHCHECK_URL=http://localhost:8080/health",
        "HEALTHCHECK_URL=http://localhost:8081/health",
        "deploy.yml",
    ),
    "app/server.py": (
        'paid = sum(order["total"] for order',
        'paid = sum(order["amount"] for order',
        "tests.yml",
    ),
    "staging/orders-api.json": (
        '"exportCsv": false\n',
        '"exportCsv": false,\n',
        "staging.yml",
    ),
    "release/release.env": (
        "MIGRATION_SCRIPT=release/scripts/migrate.sh",
        "MIGRATION_SCRIPT=release/Scripts/migrate.sh",
        "release.yml",
    ),
    "reports/reports.env": (
        "STARTUP_TIMEOUT_SECONDS=20\n",
        "STARTUP_TIMEOUT_SECONDS=5\n",
        "reports.yml",
    ),
}
CASES = {workflow.removesuffix(".yml"): path for path, (_, _, workflow) in BREAKS.items()}


def gh(*args, body=None):
    command = ["gh", "api", *args]
    if body is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(body) if body is not None else None,
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"gh api {args[0]} failed: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    global REPO
    parser = argparse.ArgumentParser(description="Reintroduce the demo failures.")
    parser.add_argument("cases", nargs="*", metavar="case",
                        help=f"cases to break ({', '.join(CASES)}); all of them when omitted")
    parser.add_argument("--repo", default=REPO, help=f"repository (default {REPO})")
    args = parser.parse_args()
    unknown = [case for case in args.cases if case not in CASES]
    if unknown:
        parser.error(f"unknown case {', '.join(unknown)}; choose from {', '.join(CASES)}")
    REPO = args.repo
    paths = [CASES[case] for case in args.cases] if args.cases else list(BREAKS)

    head = gh(f"repos/{REPO}/git/ref/heads/{BRANCH}")["object"]["sha"]
    base_tree = gh(f"repos/{REPO}/git/commits/{head}")["tree"]["sha"]

    changes, dispatch = [], []
    for path in paths:
        fixed, failing, workflow = BREAKS[path]
        blob = gh(f"repos/{REPO}/contents/{path}?ref={head}")
        text = base64.b64decode(blob["content"]).decode("utf-8")
        if failing in text:
            print(f"{path}: already failing")
            dispatch.append(workflow)
        elif fixed in text:
            print(f"{path}: restoring the failure")
            changes.append({"path": path, "mode": "100644", "type": "blob",
                            "content": text.replace(fixed, failing, 1)})
        else:
            sys.exit(f"{path}: neither the fixed nor the failing text was found; fix the file by hand")

    if changes:
        tree = gh(f"repos/{REPO}/git/trees", "-X", "POST", body={"base_tree": base_tree, "tree": changes})
        commit = gh(f"repos/{REPO}/git/commits", "-X", "POST", body={
            "message": "chore(demo): reintroduce the demo failures",
            "tree": tree["sha"],
            "parents": [head],
        })
        gh(f"repos/{REPO}/git/refs/heads/{BRANCH}", "-X", "PATCH", body={"sha": commit["sha"]})
        print(f"Pushed {commit['sha'][:7]} to {BRANCH}: the push runs "
              + ", ".join(BREAKS[c["path"]][2] for c in changes))

    for workflow in dispatch:
        subprocess.run(["gh", "workflow", "run", workflow, "--repo", REPO, "--ref", BRANCH], check=True)
        print(f"Dispatched {workflow}")


if __name__ == "__main__":
    main()
