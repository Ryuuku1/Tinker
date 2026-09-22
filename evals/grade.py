"""Grade attributed observations offline; never execute providers or source text.

Facts are normalized by a human from native traces. Hashes bind those facts to a
reviewable source, but cannot prove the interpretation is true or complete.
"""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys

MAX_BYTES = 10 * 1024 * 1024
ACTIVITY_FIELDS = frozenset({'workers_total', 'peak_active_helpers',
                             'peak_active_writers', 'returned_workers'})


def valid_lines(lines, count):
    return (isinstance(lines, list) and len(lines) == 2 and
            all(type(n) is int for n in lines) and 1 <= lines[0] <= lines[1] <= count)


def measure_activity(activity, line_count):
    """Derive counts from human-normalized native events, not asserted totals.

    Completeness and event interpretation still require human review of the source.
    Unknown termination stays active; a result is distinct from stopping execution.
    """
    if activity is None:
        return None
    if (not isinstance(activity, dict) or set(activity) != {'complete', 'lines', 'events'} or
            type(activity['complete']) is not bool or not isinstance(activity['events'], list) or
            not valid_lines(activity['lines'], line_count)):
        raise ValueError('Activity requires completeness, coverage lines and an event list')
    active, known, writers, returned = set(), set(), set(), set()
    peak_helpers = peak_writers = 0
    last_line = activity['lines'][0]
    for event in activity['events']:
        if not isinstance(event, dict) or set(event) != {'event', 'actor', 'lines'}:
            raise ValueError('Activity event requires event, actor and lines')
        actor, action, lines = event['actor'], event['event'], event['lines']
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError('Activity actor must be a native identity or lead')
        if (not valid_lines(lines, line_count) or lines[0] < last_line or
                lines[0] < activity['lines'][0] or lines[1] > activity['lines'][1]):
            raise ValueError('Activity provenance must be ordered within source coverage')
        last_line = lines[0]
        if action == 'start_helper':
            if actor == 'lead' or actor in active:
                raise ValueError('Helper is already active or is the Lead')
            known.add(actor)
            active.add(actor)
        elif action == 'stop_helper':
            if actor not in active or actor in writers:
                raise ValueError('Cannot stop an unknown, stopped or writing helper')
            active.remove(actor)
        elif action == 'result':
            if actor not in known:
                raise ValueError('A result needs an actual helper identity')
            returned.add(actor)
        elif action == 'start_write':
            if actor in writers or (actor != 'lead' and actor not in active):
                raise ValueError('Writer must be the Lead or an active helper, and not already writing')
            writers.add(actor)
        elif action == 'stop_write':
            if actor not in writers:
                raise ValueError('Cannot stop an inactive writer')
            writers.remove(actor)
        else:
            raise ValueError('Unknown activity event')
        peak_helpers = max(peak_helpers, len(active))
        peak_writers = max(peak_writers, len(writers))
    return {'workers_total': len(known), 'peak_active_helpers': peak_helpers,
            'peak_active_writers': peak_writers, 'returned_workers': len(returned)}


def read_text(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Evidence file exceeds the 10 MiB limit; select a redacted excerpt")
    return data, data.decode("utf-8-sig")


def unique_object(pairs):
    """Reject ambiguous records rather than let the last duplicate fact win."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def grade(case, record, directory):
    """Return a grade without changing evidence, instructions or repositories."""
    result = {"case": case.get("id") if isinstance(case, dict) else None, "status": "invalid", "checks": []}
    try:
        if not isinstance(case, dict) or not isinstance(record, dict):
            raise ValueError("Case and record must be objects")
        if record.get("case_id") != case.get("id") or not isinstance(case.get("id"), str):
            raise ValueError("Record must identify this exact case")
        origin = record.get("origin")
        if origin not in ("synthetic", "observed"):
            raise ValueError("Origin must be synthetic or observed")
        result["origin"] = origin
        prefix = "fixture-" if origin == "synthetic" else ""
        rules = case.get("rules")
        if not isinstance(rules, list) or not rules:
            raise ValueError("A case needs nonempty rules")
        fields = set()
        for rule in rules:
            if not isinstance(rule, dict) or set(rule) != {"field", "op", "value"}:
                raise ValueError("Rule requires exactly field, op and value")
            field = rule["field"]
            if not isinstance(field, str) or not field or field in fields:
                raise ValueError("Rule fields must be unique nonempty strings")
            fields.add(field)
            if rule["op"] not in ("eq", "lte", "gte"):
                raise ValueError("Unsupported comparison")
            if type(rule["value"]) not in (str, int, bool):
                raise ValueError("Expected values must be strings, integers or booleans")
            if field in ACTIVITY_FIELDS and type(rule['value']) is not int:
                raise ValueError('Activity comparisons require integer counts')
            if rule["op"] != "eq" and type(rule["value"]) is not int:
                raise ValueError("Ordered comparisons require integers")
        observations = record.get("observations")
        if not isinstance(observations, dict) or not set(observations).issubset(fields):
            raise ValueError("Unknown or malformed observations")
        if set(observations) & ACTIVITY_FIELDS:
            raise ValueError('Activity counts must come from events, not scalar observations')
        source = record.get("source")
        if not isinstance(source, dict) or not source.get("path"):
            result.update(status=prefix + "not-verified", reason="Source is missing")
            return result
        source_name = source["path"]
        if not isinstance(source_name, str):
            raise ValueError("Source path must be a string")
        relative = Path(source_name.replace("\\", "/"))
        if relative.is_absolute() or PureWindowsPath(source_name).drive or ".." in relative.parts:
            raise ValueError("Source must be a relative path inside the record directory")
        base = Path(directory).resolve()
        path = (base / relative).resolve()
        if not path.is_relative_to(base):
            raise ValueError("Source escapes the record directory")
        try:
            raw, text = read_text(path)
        except FileNotFoundError:
            result.update(status=prefix + "not-verified", reason="Source file is missing")
            return result
        digest = source.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError("Source needs a SHA-256 digest")
        if hashlib.sha256(raw).hexdigest() != digest.lower():
            raise ValueError("Source digest mismatch")
        if not text.strip():
            result.update(status=prefix + "not-verified", reason="Source is empty")
            return result
        line_count = len(text.splitlines())
        activity = record.get('activity')
        counts = measure_activity(activity, line_count)
        if counts is not None:
            result['activity_counts'] = counts
            result['activity_complete'] = activity['complete']
        for rule in rules:
            observation = observations.get(rule["field"])
            if rule['field'] in ACTIVITY_FIELDS and counts is not None:
                measured = counts[rule['field']]
                # Partial traces give lower bounds: an excess proves failure,
                # but a count below a limit cannot establish absence or success.
                proven_excess = rule['op'] in ('lte', 'eq') and measured > rule['value']
                if activity['complete'] or proven_excess:
                    observation = {'value': measured, 'lines': activity['lines']}
            check = {"field": rule["field"], "status": "not-verified"}
            result["checks"].append(check)
            if observation is None:
                continue
            if not isinstance(observation, dict) or set(observation) != {"value", "lines"}:
                raise ValueError("Observation requires exactly value and lines")
            lines = observation["lines"]
            if not valid_lines(lines, line_count):
                continue
            actual, expected = observation["value"], rule["value"]
            if type(actual) is not type(expected):
                raise ValueError("Observation type must match rule type")
            if type(actual) is int and actual < 0:
                raise ValueError("Counts and exit codes must be normalized to nonnegative integers")
            op = rule["op"]
            passed = actual == expected if op == "eq" else actual <= expected if op == "lte" else actual >= expected
            check.update(status="passed" if passed else "failed", actual=actual,
                         expected=expected, op=op, lines=lines)
        statuses = {check["status"] for check in result["checks"]}
        status = "failed" if "failed" in statuses else "not-verified" if "not-verified" in statuses else "passed"
        result["status"] = prefix + status
    except (OSError, ValueError, TypeError, KeyError) as error:
        result.update(status="invalid", reason=str(error))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="JSON observation record; no command execution")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    args = parser.parse_args(argv)
    try:
        record = json.loads(read_text(args.record)[1], object_pairs_hook=unique_object)
        cases = json.loads(read_text(args.cases)[1], object_pairs_hook=unique_object)
        if not isinstance(record, dict) or not isinstance(cases, list):
            raise ValueError("Record must be an object and cases a list")
        matching = [case for case in cases if isinstance(case, dict) and case.get("id") == record.get("case_id")]
        if len(matching) != 1:
            raise ValueError("Expected exactly one matching case")
        result = grade(matching[0], record, args.record.parent)
    except (OSError, ValueError, TypeError) as error:
        result = {"status": "invalid", "reason": str(error)}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("passed", "fixture-passed") else 1


if __name__ == "__main__":
    sys.exit(main())
