"""Tokens and estimated cost per workflow, from the local transcripts of coding-agent hosts.

    python scripts/usage_report.py [--days 7] [--json] [--cache-detail] [--claude-dir DIR] [--codex-dir DIR]

Claude Code: every *.jsonl under the projects folder (subagent transcripts count toward their parent session) changed
in the last N days; each API response counts once. A session is attributed to the first Tinker workflow it used (a Skill
tool call or slash command naming tinker); a plain tinker is the front door; anything else is "other". The workflow
table counts every request in those files, so a chat that began before the window counts in full. The cache lines count
only requests made inside the window, by request time, each response once across all files: the share read from the
prompt cache, the cost split, rebuilds after the cache expired, compactions, the first request of a new chat per project
folder and the helpers' share. Costs are estimates at API list prices (PRICES_AS_OF) and are comparable between weeks
and workflows, not with an invoice.
Codex: rollout files, last cumulative token total per session, tokens only. Antigravity is not supported. Message
content is never printed. Standard library only.
"""
import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

PRICES_AS_OF = "2026-11"
# USD per million tokens: input, output, cache read. Cache writes cost 1.25x input (5 minutes) or 2x input (1 hour).
PRICES = {"fable": (8.0, 40.0, 0.20), "opus": (4.0, 20.0, 0.20), "sonnet": (2.0, 10.0, 0.10), "haiku": (0.10, 0.50, 0.01)}
COMMAND = re.compile(r"<command-name>/(tinker[^<\s]*)")
CODEX_SKILL = re.compile(r"<skill>\s*<name>([^<\s]*tinker[^<\s]*)</name>|\$(tinker[\w:-]*)")
FRONT_DOOR = "front-door"
FIELDS = ("input", "cache_read", "cache_write", "output")


def family(model):
    model = (model or "").lower()
    return next((name for name in PRICES if name in model), None)


def workflow_from_name(name):
    """tinker:implement, tinker-implement, tinker:tinker-implement -> implement; plain tinker -> front-door."""
    tokens = [token for token in re.split(r"[:\-_/ .]+", (name or "").lower()) if token]
    if "tinker" not in tokens:
        return None
    rest = [token for token in tokens if token != "tinker"]
    return "-".join(rest) or FRONT_DOOR


def cost_parts(model, usage):
    """Estimated USD for one request split into input, read, write and output, or None for a model without prices."""
    name = family(model)
    if not name:
        return None
    price_in, price_out, price_read = PRICES[name]
    write_1h = min(usage["cache_write_1h"], usage["cache_write"])
    write_5m = usage["cache_write"] - write_1h  # a write with no split counts as 5-minute
    return {"input": usage["input"] * price_in / 1e6, "read": usage["cache_read"] * price_read / 1e6,
            "write": (write_5m * 1.25 + write_1h * 2) * price_in / 1e6, "output": usage["output"] * price_out / 1e6}


def request_cost(model, usage):
    """Estimated USD for one request, or None for a model without prices."""
    parts = cost_parts(model, usage)
    return None if parts is None else sum(parts.values())


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def claude_usage(raw):
    split = raw.get("cache_creation") if isinstance(raw.get("cache_creation"), dict) else {}
    one_hour = number(split.get("ephemeral_1h_input_tokens"))
    five_minutes = number(split.get("ephemeral_5m_input_tokens"))
    write = number(raw.get("cache_creation_input_tokens")) or one_hour + five_minutes
    return {"input": number(raw.get("input_tokens")), "output": number(raw.get("output_tokens")),
            "cache_read": number(raw.get("cache_read_input_tokens")), "cache_write": write, "cache_write_1h": one_hour}


def read_jsonl(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


def message_texts(message):
    content = message.get("content")
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                yield block["text"]


def claude_workflow(entry):
    message = entry.get("message")
    if not isinstance(message, dict):
        return None
    if entry.get("type") == "assistant" and isinstance(message.get("content"), list):
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                skill = (block.get("input") or {}).get("skill") if isinstance(block.get("input"), dict) else None
                if isinstance(skill, str) and workflow_from_name(skill):
                    return workflow_from_name(skill)
    elif entry.get("type") == "user":
        for text in message_texts(message):
            found = COMMAND.search(text)
            if found and workflow_from_name(found.group(1)):
                return workflow_from_name(found.group(1))
    return None


def new_session():
    return {"workflow": None, "requests": 0, "input": 0, "cache_read": 0, "cache_write": 0, "output": 0, "cost": 0.0,
            "unpriced": set(), "seen": set()}


def read_claude_session(files, session):
    for path in files:
        for entry in read_jsonl(path):
            if not session["workflow"]:
                session["workflow"] = claude_workflow(entry)
            message = entry.get("message")
            if entry.get("type") != "assistant" or not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
                continue
            key = f"{message.get('id') or ''}|{entry.get('requestId') or ''}"
            if key != "|":
                if key in session["seen"]:
                    continue
                session["seen"].add(key)
            usage = claude_usage(message["usage"])
            if not any(usage[field] for field in FIELDS):
                continue
            session["requests"] += 1
            for field in FIELDS:
                session[field] += usage[field]
            cost = request_cost(message.get("model"), usage)
            if cost is None:
                session["unpriced"].add(str(message.get("model") or "unknown"))
            else:
                session["cost"] += cost


def recent(directory, pattern, days):
    cutoff = time.time() - days * 86400
    found = []
    if Path(directory).is_dir():
        for path in Path(directory).rglob(pattern):
            try:
                if path.is_file() and path.stat().st_mtime >= cutoff:
                    found.append(path)
            except OSError:
                continue
    return sorted(found)


def claude_sessions(directory, days):
    groups = {}
    for path in recent(directory, "*.jsonl", days):
        if path.parent.name == "subagents":
            key = (str(path.parent.parent.parent), path.parent.parent.name)
        else:
            key = (str(path.parent), path.stem)
        groups.setdefault(key, []).append(path)
    sessions = []
    for files in groups.values():
        files.sort(key=lambda path: (path.parent.name == "subagents", str(path)))
        session = new_session()
        read_claude_session(files, session)
        if session["requests"]:
            sessions.append(session)
    return sessions


def stamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def cache_threads(path, helper):
    """[(is_helper, requests in time order)] for one transcript: the chat and each helper thread apart."""
    threads = {}
    for entry in read_jsonl(path):
        message = entry.get("message")
        when = stamp(entry.get("timestamp"))
        if (entry.get("type") != "assistant" or not isinstance(message, dict) or not isinstance(message.get("usage"), dict)
                or when is None or not message.get("id")):
            continue
        side = helper or bool(entry.get("isSidechain"))
        requests = threads.setdefault((side, entry.get("agentId") if side else None), {})
        blocks = message["content"] if isinstance(message.get("content"), list) else []
        tools = sum(1 for block in blocks if isinstance(block, dict) and block.get("type") == "tool_use")
        usage = claude_usage(message["usage"])
        old = requests.get(message["id"])
        if old:  # one row per content block: the same response again
            old.update(start=min(old["start"], when), end=max(old["end"], when), tools=old["tools"] + tools)
            old["usage"]["output"] = max(old["usage"]["output"], usage["output"])
        else:
            requests[message["id"]] = {"id": message["id"], "start": when, "end": when, "model": message.get("model"),
                                       "tools": tools, "usage": usage}
    return [(side, sorted(reqs.values(), key=lambda r: r["start"])) for (side, _), reqs in threads.items()]


def context(request):
    usage = request["usage"]
    return usage["input"] + usage["cache_read"] + usage["cache_write"]


def mtime(path):
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def spread(values):
    values = sorted(values)
    return {"median": int(statistics.median(values)), "p25": values[len(values) // 4], "max": values[-1]}


def cache_lines(directory, days):
    """Prompt-cache measures for requests made in the last N days, by request time."""
    since = time.time() - days * 86400
    seen, folders, after = set(), {}, []
    main = {"chats": 0, "requests": 0, "input": 0, "cache_read": 0, "cache_write": 0, "tools": [0, 0, 0, 0],
            "usd": dict.fromkeys(("input", "read", "write", "output"), 0.0)}
    rebuilds, compactions = [0, 0.0], [0, 0.0]
    helpers = {"threads": 0, "requests": 0, "usd": 0.0, "families": {}}
    # the oldest file owns a response, so history copied into a resumed chat counts once
    for path in sorted(recent(directory, "*.jsonl", days), key=lambda found: (mtime(found), str(found))):
        parts = path.relative_to(directory).parts
        for side, reqs in cache_threads(path, "subagents" in parts):
            new = [r["id"] not in seen for r in reqs]
            seen.update(r["id"] for r in reqs)
            if not any(fresh and r["start"] >= since for r, fresh in zip(reqs, new)):
                continue
            (helpers if side else main)["threads" if side else "chats"] += 1
            prev, ttl, first = None, None, True
            for index, (r, fresh) in enumerate(zip(reqs, new)):
                usage, size = r["usage"], context(r)
                ttl = 60 if usage["cache_write_1h"] else 5 if usage["cache_write"] else ttl
                counted = fresh and r["start"] >= since
                cost = cost_parts(r["model"], usage) or dict.fromkeys(main["usd"], 0.0)
                if counted and side:
                    helpers["requests"] += 1
                    helpers["usd"] += sum(cost.values())
                    name = family(r["model"]) or "unpriced"
                    helpers["families"][name] = helpers["families"].get(name, 0) + 1
                elif counted:
                    main["requests"] += 1
                    for field in ("input", "cache_read", "cache_write"):
                        main[field] += usage[field]
                    for field, value in cost.items():
                        main["usd"][field] += value
                    main["tools"][min(r["tools"], 2)] += 1
                    main["tools"][3] += r["tools"]
                    if first and index == 0:
                        folders.setdefault(parts[0], []).append(size)
                    if prev and prev["size"] >= 5_000 and usage["cache_read"] < prev["size"] / 2:
                        if ttl and r["start"] - prev["end"] > ttl * 60:
                            rebuilds[0] += 1
                            rebuilds[1] += cost["write"]
                        elif size < prev["size"] * 0.7:
                            following = reqs[index + 1] if index + 1 < len(reqs) else None
                            if not (following and context(following) >= prev["size"] * 0.9):  # else a side request
                                compactions[0] += 1
                                compactions[1] += cost["write"]
                                after.append(size)
                first = first and not counted
                prev = {"end": r["end"], "size": size}
    requests = main["requests"] or 1
    main_usd = sum(main["usd"].values())
    return {
        "window": f"requests made in the last {days} days, by request time",
        "main": {
            "chats": main["chats"], "requests": main["requests"], "est_usd": round(main_usd, 4),
            "hit_rate": round(main["cache_read"] / ((main["cache_read"] + main["cache_write"] + main["input"]) or 1), 4),
            "usd_split": {field: round(value, 4) for field, value in main["usd"].items()},
            "usd_per_request": round(main_usd / requests, 4),
            "tool_calls_per_request": round(main["tools"][3] / requests, 2),
            "tool_call_shares": dict(zip(("none", "one", "more"), (round(n / requests, 4) for n in main["tools"][:3]))),
            "expired_rebuilds": {"count": rebuilds[0], "est_usd": round(rebuilds[1], 4)},
            "compactions": {"count": compactions[0], "est_usd": round(compactions[1], 4),
                            "median_context_after": int(statistics.median(after)) if after else None},
            "first_request_by_folder": [dict(folder=name, chats=len(sizes), **spread(sizes)) for name, sizes in
                                        sorted(folders.items(), key=lambda item: (-len(item[1]), item[0]))]},
        "helpers": {"threads": helpers["threads"], "requests": helpers["requests"], "est_usd": round(helpers["usd"], 4),
                    "share_of_usd": round(helpers["usd"] / ((main_usd + helpers["usd"]) or 1), 4),
                    "requests_by_family": dict(sorted(helpers["families"].items()))}}


def codex_text(payload):
    content = payload.get("content")
    if isinstance(content, list):
        return "\n".join(block["text"] for block in content if isinstance(block, dict) and isinstance(block.get("text"), str))
    return content if isinstance(content, str) else ""


def read_codex_file(path):
    """(session id, workflow, models, last cumulative total, request count) of one rollout file."""
    session_id, workflow, models, total, requests, last_sum = None, None, set(), None, 0, -1
    for entry in read_jsonl(path):
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue
        kind = entry.get("type")
        if kind == "session_meta" and not session_id:
            session_id = payload.get("session_id") or payload.get("id")
        elif kind == "turn_context" and isinstance(payload.get("model"), str):
            models.add(payload["model"])
        elif kind == "response_item" and payload.get("type") == "message" and payload.get("role") == "user" and not workflow:
            found = CODEX_SKILL.search(codex_text(payload))
            workflow = workflow_from_name(found.group(1) or found.group(2)) if found else None
        elif kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            usage = info.get("total_token_usage") if isinstance(info, dict) else None
            if isinstance(usage, dict):
                total = usage
                if number(usage.get("total_tokens")) != last_sum:
                    requests += 1
                    last_sum = number(usage.get("total_tokens"))
    return session_id or path.stem, workflow, models, total, requests


def codex_sessions(directory, days):
    groups = {}
    for path in recent(directory, "rollout-*.jsonl", days):
        session_id, workflow, models, total, requests = read_codex_file(path)
        if not total:
            continue
        session = groups.setdefault(session_id, new_session())
        session["workflow"] = session["workflow"] or workflow
        session["requests"] += requests
        cached = number(total.get("cached_input_tokens"))
        session["input"] += max(0, number(total.get("input_tokens")) - cached)  # input_tokens includes the cached part
        session["cache_read"] += cached
        session["cache_write"] += number(total.get("cache_write_input_tokens"))
        session["output"] += number(total.get("output_tokens"))
    return [session for session in groups.values() if any(session[field] for field in FIELDS)]


def aggregate(sessions, priced):
    rows, unpriced = {}, set()
    for session in sessions:
        name = session["workflow"] or "other"
        row = rows.setdefault(name, {"workflow": name, "sessions": 0, "requests": 0, "input": 0, "cache_read": 0,
                                     "cache_write": 0, "output": 0, "est_usd": 0.0 if priced else None})
        row["sessions"] += 1
        row["requests"] += session["requests"]
        for field in FIELDS:
            row[field] += session[field]
        if priced:
            row["est_usd"] += session["cost"]
            unpriced |= session["unpriced"]
    result = []
    for row in rows.values():
        context = row["input"] + row["cache_read"] + row["cache_write"]
        row["avg_context"] = round(context / max(1, row["requests"]))
        row["usd_per_session"] = round(row["est_usd"] / row["sessions"], 4) if priced else None
        row["est_usd"] = round(row["est_usd"], 4) if priced else None
        result.append(row)
    result.sort(key=lambda row: (-(row["est_usd"] or 0), -(row["input"] + row["cache_read"] + row["cache_write"] + row["output"]), row["workflow"]))
    return result, sorted(unpriced)


def build_report(days, claude_dir, codex_dir):
    claude_rows, unpriced = aggregate(claude_sessions(claude_dir, days), True)
    codex_rows, _ = aggregate(codex_sessions(codex_dir, days), False)
    return {"days": days, "prices_as_of": PRICES_AS_OF,
            "hosts": [{"host": "claude", "workflows": claude_rows, "unpriced_models": unpriced,
                       "cache": cache_lines(Path(claude_dir), days) if Path(claude_dir).is_dir() else None},
                      {"host": "codex", "workflows": codex_rows, "unpriced_models": []},
                      {"host": "antigravity", "supported": False, "workflows": [], "unpriced_models": []}]}


def render_cache(cache, detail):
    main, helpers = cache["main"], cache["helpers"]
    out = [f"Cache, main chats ({cache['window']}):"]
    if not main["requests"]:
        return out + ["  no requests in the window"]
    split, total = main["usd_split"], main["est_usd"] or 1
    rebuilds, compactions, folders = main["expired_rebuilds"], main["compactions"], main["first_request_by_folder"]
    after = compactions["median_context_after"]
    families = sorted(helpers["requests_by_family"].items(), key=lambda item: -item[1])
    out += [f"  {main['chats']} chats, {main['requests']:,} requests, ${main['est_usd']:,.2f}; per request "
            f"${main['usd_per_request']:.3f} and {main['tool_calls_per_request']:.2f} tool calls",
            f"  {main['hit_rate']:.1%} of input read from the cache; cost: read {split['read'] / total:.0%}, "
            f"write {split['write'] / total:.0%}, output {split['output'] / total:.0%}",
            f"  rebuilds after the cache expired {rebuilds['count']} (${rebuilds['est_usd']:,.2f}); compactions "
            f"{compactions['count']} (${compactions['est_usd']:,.2f})"
            + (f", median {after / 1000:.0f}k left after" if after else ""),
            "  first request of a new chat, median by folder: "
            + (", ".join(f"{f['folder']} {f['median'] / 1000:.0f}k ({f['chats']})" for f in folders[:3]) or "none"),
            f"  helpers: {helpers['share_of_usd']:.0%} of the cost; requests by family: "
            + (", ".join(f"{name} {count / (helpers['requests'] or 1):.0%}" for name, count in families) or "none")]
    if detail:
        shares = main["tool_call_shares"]
        out.append(f"  tool calls per request: none {shares['none']:.0%}, one {shares['one']:.0%}, two or more "
                   f"{shares['more']:.0%}; helpers ${helpers['est_usd']:,.2f} in {helpers['threads']} threads")
        out += [f"  first request in {f['folder']}: {f['chats']} chats, p25 {f['p25']:,}, median {f['median']:,}, "
                f"max {f['max']:,}" for f in folders]
    return out


def render(report, cache_detail=False):
    out = [f"Usage, last {report['days']} days (estimates at API list prices as of {report['prices_as_of']})"]
    for host in report["hosts"]:
        out.append("")
        if host.get("supported") is False:
            out.append(f"{host['host']}: not supported (no local transcript format verified)")
            continue
        out.append(f"{host['host']}" + (" (tokens only, no prices)" if host["host"] == "codex" else ""))
        if host["host"] == "claude":
            out.append(f"Workflows: every request in transcripts changed in the last {report['days']} days.")
        out.append("| Workflow | Sessions | Requests | Avg context | Output | Est. USD | USD/session |")
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in host["workflows"]:
            usd = "-" if row["est_usd"] is None else f"{row['est_usd']:.2f}"
            per = "-" if row["usd_per_session"] is None else f"{row['usd_per_session']:.2f}"
            out.append(f"| {row['workflow']} | {row['sessions']} | {row['requests']} | {row['avg_context'] / 1000:.0f}k "
                       f"| {row['output'] / 1e6:.2f}M | {usd} | {per} |")
        if not host["workflows"]:
            out.append("(no sessions in the window)")
        if host["unpriced_models"]:
            out.append("Unpriced models (tokens counted, no cost): " + ", ".join(host["unpriced_models"]))
        if host.get("cache"):
            out += [""] + render_cache(host["cache"], cache_detail)
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=7,
                        help="workflows: transcripts changed in the last N days; cache lines: requests made in them")
    parser.add_argument("--cache-detail", action="store_true", help="add tool-call shares and every folder's first request")
    parser.add_argument("--json", action="store_true", help="print JSON instead of tables")
    parser.add_argument("--claude-dir", default=str(Path.home() / ".claude" / "projects"))
    parser.add_argument("--codex-dir", default=str(Path.home() / ".codex" / "sessions"))
    args = parser.parse_args(argv)
    report = build_report(args.days, args.claude_dir, args.codex_dir)
    print(json.dumps(report, indent=2) if args.json else render(report, args.cache_detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
