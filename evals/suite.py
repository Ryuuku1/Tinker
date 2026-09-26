"""Accept or compare evaluation runs offline from a suite manifest; never launches a provider.

A manifest names one case set, the hosts evaluated (version and model), the evaluation
configuration and one run per host and case: an observation record graded by grade.py, the
human review of that case's manual criteria, and cost, tokens or duration only when measured.

Expected coverage comes from the catalog, never from the runs present: every case of the set
that applies to a declared host needs exactly one run. Acceptance also needs every declared
human review complete, and live acceptance accepts observed evidence only.

  python evals/suite.py <manifest.json> [--cases evals/cases.json]
  python evals/suite.py compare <before.json> <after.json> [--cases C] [--after-cases C2]
"""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402  (the evidence grader this suite builds on)

HOSTS = ("claude", "codex", "antigravity")
SETS = ("regression", "held-out")
MANIFEST_KEYS = {"set", "acceptance", "configuration", "hosts", "runs"}
RUN_KEYS = {"host", "case", "record", "review", "metrics"}
METRICS = {"tokens", "cost", "duration_seconds"}


def load(path):
    return json.loads(grade.read_text(path)[1], object_pairs_hook=grade.unique_object)


def set_digest(cases, name):
    """Identity of one set's case definitions: a changed or weakened case is a different evaluation."""
    chosen = sorted((c for c in cases if isinstance(c, dict) and c.get("set") == name), key=lambda c: str(c.get("id")))
    return hashlib.sha256(json.dumps(chosen, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def inside(base, name):
    """A path relative to the manifest folder that stays inside it, or None."""
    if not isinstance(name, str) or not name:
        return None
    relative = Path(name.replace("\\", "/"))
    if relative.is_absolute() or PureWindowsPath(name).drive or ".." in relative.parts:
        return None
    path = (base / relative).resolve()
    return path if path.is_relative_to(base) else None


def check_manifest(manifest, cases):
    """Problems that make the manifest unusable; a usable one yields no problems."""
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        return [f"a manifest has exactly the fields {sorted(MANIFEST_KEYS)}"]
    problems = []
    if manifest["set"] not in SETS:
        problems.append(f"set must be one of {SETS}")
    if manifest["acceptance"] not in ("live", "fixture"):
        problems.append("acceptance must be live or fixture")
    if not isinstance(manifest["configuration"], str) or not manifest["configuration"].strip():
        problems.append("configuration must name the evaluation setup")
    hosts = manifest["hosts"]
    if not isinstance(hosts, dict) or not hosts or not set(hosts) <= set(HOSTS) or any(
            not isinstance(v, dict) or set(v) != {"version", "model"} or not all(isinstance(v[k], str) and v[k].strip()
                                                                          for k in v) for v in hosts.values()):
        problems.append("hosts maps each evaluated host to its version and model")
    if not isinstance(manifest["runs"], list):
        problems.append("runs must be a list")
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    if len(ids) != len(cases) or len(set(ids)) != len(ids):
        problems.append("the case catalog needs unique case objects")
    return problems


def check_metrics(metrics):
    if metrics is None:
        return []
    if not isinstance(metrics, dict) or not set(metrics) <= METRICS:
        return [f"metrics may only report {sorted(METRICS)}"]
    return [f"metric {name} needs a nonnegative number and its measurement source" for name, m in metrics.items()
            if not isinstance(m, dict) or set(m) != {"value", "source"} or type(m["value"]) not in (int, float)
            or m["value"] < 0 or not isinstance(m["source"], str) or not m["source"].strip()]


def review_state(review):
    if review is None:
        return "missing"
    if not isinstance(review, dict) or not {"reviewer", "date", "complete"} <= set(review) or \
            type(review["complete"]) is not bool or not all(isinstance(review[k], str) and review[k].strip()
                                                             for k in ("reviewer", "date")):
        return "malformed"
    return "complete" if review["complete"] else "incomplete"


def evaluate(path, cases_path):
    """Grade every run of a suite manifest and decide acceptance; files are only read."""
    path = Path(path)
    try:
        manifest, cases = load(path), load(cases_path)
        if not isinstance(cases, list):
            raise ValueError("the case catalog must be a list")
    except (OSError, ValueError) as error:
        return {"status": "invalid", "problems": [str(error)], "runs": []}
    problems = check_manifest(manifest, cases)
    if problems:
        return {"status": "invalid", "problems": problems, "runs": []}
    base, catalog = path.parent.resolve(), {c["id"]: c for c in cases}
    hosts, chosen = manifest["hosts"], manifest["set"]
    expected = {(h, c["id"]) for c in cases if c.get("set") == chosen for h in hosts if h in c.get("hosts", HOSTS)}
    seen, runs, invalid, rejected, pending = set(), [], [], [], []
    for run in manifest["runs"]:
        if not isinstance(run, dict) or not {"host", "case", "record"} <= set(run) or not set(run) <= RUN_KEYS:
            invalid.append(f"a run has host, case and record, and optionally review and metrics: {run!r}"[:300])
            continue
        key, label = (run["host"], run["case"]), f"{run['host']}/{run['case']}"
        if key in seen:
            invalid.append(f"duplicate run for {label}")
            continue
        seen.add(key)
        if key not in expected:
            case = catalog.get(run["case"])
            reason = ("is not a case in the catalog" if case is None else f"belongs to set {case.get('set')}"
                      if case.get("set") != chosen else "is for a host this manifest does not declare"
                      if run["host"] not in hosts else "does not apply to that host")
            invalid.append(f"unexpected run for {label}: the case {reason}")
            continue
        record_path = inside(base, run["record"])
        metrics_problems = check_metrics(run.get("metrics"))
        review = review_state(run.get("review"))
        if record_path is None or metrics_problems or review == "malformed":
            invalid.extend([f"{label}: record must be a relative path inside the manifest folder"] * (record_path is None)
                           + [f"{label}: {p}" for p in metrics_problems]
                           + [f"{label}: review needs reviewer, date and a boolean complete"] * (review == "malformed"))
            continue
        try:
            graded = grade.grade(catalog[run["case"]], load(record_path), record_path.parent)
        except (OSError, ValueError) as error:
            graded = {"status": "invalid", "reason": str(error)}
        machine = graded["status"]
        if machine in ("passed", "fixture-passed") and (manifest["acceptance"] == "fixture" or machine == "passed"):
            verdict = "accepted" if review == "complete" else "not-verified"
            if review != "complete":
                pending.append(f"{label}: human review is {review}")
        elif machine.startswith("fixture-") and manifest["acceptance"] == "live":
            verdict = "rejected"
            rejected.append(f"{label}: synthetic evidence cannot establish live acceptance")
        elif machine.endswith("not-verified"):
            verdict = "not-verified"
            pending.append(f"{label}: machine checks not verified ({graded.get('reason', 'missing observations')})")
        else:
            verdict = "rejected"
            rejected.append(f"{label}: machine checks {machine}" + (f" ({graded['reason']})" if graded.get("reason") else ""))
        runs.append({"host": run["host"], "case": run["case"], "machine": machine, "review": review, "verdict": verdict,
                     "checks": graded.get("checks", []), "metrics": run.get("metrics") or "unavailable"})
    pending.extend(f"missing run for {h}/{c}" for h, c in sorted(expected - seen))
    status = "invalid" if invalid else "rejected" if rejected else "not-verified" if pending else "accepted"
    return {"status": status, "set": chosen, "acceptance": manifest["acceptance"], "configuration": manifest["configuration"],
            "hosts": hosts, "cases_sha256": set_digest(cases, chosen), "problems": invalid + rejected + pending,
            "runs": sorted(runs, key=lambda r: (r["host"], r["case"]))}


def compare(before_path, after_path, cases_path, after_cases_path=None):
    """Case-level changes between two comparable evaluations; no aggregate score or threshold."""
    before, after = evaluate(before_path, cases_path), evaluate(after_path, after_cases_path or cases_path)
    reasons = [f"{name} manifest is invalid" for name, r in (("before", before), ("after", after)) if r["status"] == "invalid"]
    if not reasons:
        for field in ("set", "acceptance", "configuration", "cases_sha256"):
            if before[field] != after[field]:
                reasons.append(f"{field} differs")
        if set(before["hosts"]) != set(after["hosts"]):
            reasons.append("hosts differ")
        reasons.extend(f"{host} model differs" for host in before["hosts"]
                       if host in after["hosts"] and before["hosts"][host]["model"] != after["hosts"][host]["model"])
    if reasons:
        return {"comparable": False, "reasons": reasons}
    notes = [f"{host} version differs: {before['hosts'][host]['version']} -> {after['hosts'][host]['version']}"
             for host in before["hosts"] if before["hosts"][host]["version"] != after["hosts"][host]["version"]]
    verdicts = [{(r["host"], r["case"]): r["verdict"] for r in result["runs"]} for result in (before, after)]
    changes = [{"host": h, "case": c, "before": verdicts[0].get((h, c), "missing"), "after": verdicts[1].get((h, c), "missing")}
               for h, c in sorted(set(verdicts[0]) | set(verdicts[1])) if verdicts[0].get((h, c)) != verdicts[1].get((h, c))]
    return {"comparable": True, "notes": notes, "before": before["status"], "after": after["status"], "changes": changes,
            "regressions": [c for c in changes if c["before"] == "accepted"]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default = Path(__file__).with_name("cases.json")
    if argv[:1] == ["compare"]:
        parser.add_argument("command")
        parser.add_argument("before", type=Path)
        parser.add_argument("after", type=Path)
        parser.add_argument("--cases", type=Path, default=default)
        parser.add_argument("--after-cases", type=Path)
        args = parser.parse_args(argv)
        result = compare(args.before, args.after, args.cases, args.after_cases)
        ok = result["comparable"] and not result["regressions"]
    else:
        parser.add_argument("manifest", type=Path, help="suite manifest; evidence is read, never executed")
        parser.add_argument("--cases", type=Path, default=default)
        args = parser.parse_args(argv)
        result = evaluate(args.manifest, args.cases)
        ok = result["status"] == "accepted"
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
