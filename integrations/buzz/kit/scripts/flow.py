"""Tinker Flow: the team's conductor, with no model and no Claude credential.

The owner writes "@Tinker Flow <flow> <request>" in a kit channel. Tinker Flow posts each step of that flow
(flows.json) as a reply in the owner's thread, mentioning one agent; the agents accept it through their allowlist.
A step is done when the agent has replied and its seen and working reactions on the step are gone. Each agent gets
only the request and the earlier reports its step names, quoted as data with every @ made inert, so a quote can
never trigger another agent. Tinker Flow obeys only the owner, runs one flow at a time, and cannot loop: a flow
has a fixed list of steps. Orchestration costs no tokens.
"""
import json
import os
import re
import subprocess
import sys
import time

ACTIVE = {"👀", "💬"}  # buzz-acp's seen and working reactions; both are removed when the turn completes
FAILURE = re.compile(r"I couldn.{0,10}t process the last request")
REPORT_LIMIT = 6000  # characters of an earlier report passed to a later step


def parse(content, name="Tinker Flow"):
    """'@Tinker Flow story: add X' -> ('story', 'add X'); no command -> ('help', '')."""
    text = re.sub(rf"^\s*@?{re.escape(name)}\b[\s:,-]*", "", content.strip(), flags=re.I)
    match = re.match(r"([A-Za-z]+)[\s:,-]*(.*)", text, re.S)
    return (match.group(1).lower(), match.group(2).strip()) if match else ("help", "")


def topic(text):
    """A folder name for the work: lowercase words joined by dashes, at most 40 characters."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = ""
    for word in words:
        if len(out) + len(word) + 1 > 40:
            break
        out = f"{out}-{word}" if out else word
    return out or "flow"


def inert(text):
    """No @ in quoted text may mention anyone: the Buzz CLI turns '@Name' into a mention."""
    return text.replace("@", "＠")


def quote(text):
    text = text.strip()
    if len(text) > REPORT_LIMIT:
        text = text[:REPORT_LIMIT] + "\n[cut]"
    return "\n".join("> " + line for line in inert(text).splitlines())


def render(template, context):
    return re.sub(r"\{(\w+)\}", lambda m: context.get(m.group(1), "(none)"), template)


def root_of(event):
    for tag in event.get("tags", []):
        if tag[:1] == ["e"] and len(tag) > 1:
            return tag[1]
    return event["id"]


def mentions(event, pubkey):
    return any(tag[:2] == ["p", pubkey] for tag in event.get("tags", []))


class Flow:
    def __init__(self, client, owner, me, agents, channels, flows, poll=10, step_timeout=3600,
                 pickup_timeout=300, sleep=time.sleep, now=time.time, log=print):
        self.client, self.owner, self.me, self.agents = client, owner, me, agents
        self.channels, self.flows, self.poll = channels, flows, poll
        self.step_timeout, self.pickup_timeout = step_timeout, pickup_timeout
        self.sleep, self.now, self.log = sleep, now, log
        self.since, self.seen = int(now()), set()

    def poll_once(self):
        """Run every new owner request that mentions Tinker Flow, oldest first."""
        for channel in self.channels:
            events = sorted(self.client.messages(channel, self.since), key=lambda e: e["created_at"])
            for event in events:
                self.since = max(self.since, event["created_at"])
                if event["id"] in self.seen:
                    continue
                self.seen.add(event["id"])
                if event["pubkey"] != self.owner or not mentions(event, self.me):
                    continue
                name, request = parse(event["content"])
                if name == "stop":
                    continue  # a stop only matters while its flow runs
                root = root_of(event)
                if name not in self.flows or not request:
                    self.say(channel, root, self.help())
                    continue
                self.run(name, request, channel, root)

    def help(self):
        lines = [f"- `{name} <request>`: {flow['about']}" for name, flow in self.flows.items()]
        return "Tinker Flow runs a fixed sequence of agents for you, in one thread:\n" + "\n".join(lines) + \
            "\n\nStart one with `@Tinker Flow story <request>`; stop it with `@Tinker Flow stop` in its thread."

    def say(self, channel, root, text, notify=False):
        return self.client.send(channel, root, text, [self.owner] if notify else [])

    def run(self, name, request, channel, root):
        steps, started = self.flows[name]["steps"], self.now()
        context = {"request": inert(request), "topic": topic(request)}
        chain = " → ".join(self.agents[role]["name"] for role, _ in steps)
        self.log(f"flow {name} started in {channel} thread {root[:8]}: {chain}")
        self.say(channel, root, f"▶️ {name} flow: {chain}. To stop it, reply `@Tinker Flow stop` here.")
        for role, template in steps:
            agent = self.agents[role]
            prompt = self.client.send(channel, root, f"@{agent['name']} {render(template, context)}", [agent["hex"]])
            status, report = self.wait(channel, root, prompt, agent["hex"], started)
            self.log(f"flow {name} step {role}: {status}")
            if status != "done":
                self.say(channel, root, f"⏹️ {name} flow stopped at {agent['name']}: {status}.", notify=True)
                return
            context[role] = quote(report)
        minutes = max(1, round((self.now() - started) / 60))
        take = f" Take the work to your PC: `Copy-AgentWork {context['topic']}`." if any(
            "/work/{topic}" in template for _, template in steps) else ""
        self.say(channel, root, f"✅ {name} flow done in {minutes} min: {chain}.{take}", notify=True)

    def wait(self, channel, root, prompt, agent, started):
        """('done', the agent's last reply), or (why it stopped, None)."""
        start, picked, quiet = self.now(), False, 0
        while True:
            self.sleep(self.poll)
            thread = self.client.thread(channel, root)
            if any(e["pubkey"] == self.owner and e["created_at"] >= started and mentions(e, self.me)
                   and parse(e["content"])[0] == "stop" for e in thread):
                return "stopped by you", None
            replies = [e for e in thread if e["pubkey"] == agent and e["created_at"] >= start]
            if any(FAILURE.search(e["content"]) for e in replies):
                return "the agent could not process the step", None
            active = any(agent in r["pubkeys"] for r in self.client.reactions(prompt) if r["emoji"] in ACTIVE)
            picked = picked or active or bool(replies)
            if replies and not active:
                quiet += 1
                if quiet >= 2:  # one more poll, in case a turn ends between the reply and the reaction
                    return "done", max(replies, key=lambda e: e["created_at"])["content"]
            else:
                quiet = 0
            waited = self.now() - start
            if not picked and waited > self.pickup_timeout:
                return "it did not pick the step up (is it running?)", None
            if waited > self.step_timeout:
                return f"no answer within {self.step_timeout // 60} min", None


class Buzz:
    """The buzz CLI as Tinker Flow; flow.sh exports its key and starts the relay forwarder."""

    def __init__(self, relay):
        self.relay = relay

    def run(self, *args, stdin=None):
        done = subprocess.run(["buzz", "--relay", self.relay, *args], input=stdin, capture_output=True,
                              text=True, timeout=60)
        if done.returncode:
            raise RuntimeError(f"buzz {' '.join(args[:2])} failed: {done.stderr.strip()[:300]}")
        return done.stdout

    def messages(self, channel, since):
        return json.loads(self.run("messages", "get", "--channel", channel, "--since", str(since),
                                   "--limit", "100") or "[]")

    def thread(self, channel, root):
        return json.loads(self.run("messages", "thread", "--channel", channel, "--event", root) or "[]")

    def reactions(self, event_id):
        return json.loads(self.run("reactions", "get", "--event", event_id)).get("reactions", [])

    def send(self, channel, reply_to, text, mentions):
        args = ["messages", "send", "--channel", channel, "--reply-to", reply_to, "--content", "-"]
        for pubkey in mentions:
            args += ["--mention", pubkey]
        return re.search(r"\b[0-9a-f]{64}\b", self.run(*args, stdin=text)).group(0)


def main():
    env = os.environ
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flows.json"), encoding="utf-8") as f:
        flows = json.load(f)
    flow = Flow(Buzz(f"http://localhost:{env['KIT_PORT']}"), owner=env["FLOW_OWNER"], me=env["FLOW_SELF"],
                agents=json.loads(env["FLOW_AGENTS"]), channels=env["FLOW_CHANNELS"].split(","), flows=flows,
                poll=int(env.get("FLOW_POLL", "10")), step_timeout=int(env.get("FLOW_STEP_TIMEOUT", "3600")))
    flow.client.messages(flow.channels[0], flow.since)  # proves the relay, the key and the membership first
    print(f"flow ready: {len(flows)} flows, {len(flow.channels)} channels", flush=True)
    while True:
        try:
            flow.poll_once()
        except Exception as error:  # a relay hiccup must not end the conductor; report and keep polling
            print(f"flow poll failed: {error}", file=sys.stderr, flush=True)
        time.sleep(flow.poll)


if __name__ == "__main__":
    main()
