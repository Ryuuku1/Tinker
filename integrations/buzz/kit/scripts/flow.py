"""Tinker Flow: the team's conductor, with no model and no Claude credential.

The owner writes a request in #flows, where no mention is needed, or "@Tinker Flow <flow> <request>" in any kit
channel. A request that starts with a flow's name runs that flow (flows.json); any other gets a suggested flow,
which runs when the owner replies `go` or another flow's name in its thread. Tinker Flow posts each step as a reply
in the owner's thread, mentioning one agent; the agents accept it through their allowlist. A step is done when the
agent has replied and its seen and working reactions on the step are gone. Each agent gets only the request and
the earlier reports its step names, quoted as data with every @ made inert, so a quote can never trigger another
agent. Tinker Flow obeys only the owner, runs one flow at a time, and cannot loop: a flow has a fixed list of
steps. Orchestration costs no tokens.
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
NAME = "Tinker Flow"
GO = {"go"}  # the reply that accepts a suggested flow; everyday words such as "ok" never start one
OVERLAP = 60  # seconds re-read behind each watermark: Desktop's clock and Docker's can differ; `seen` drops repeats
# The first pattern that matches a request suggests its flow; anything else is a story.
GUESSES = (("bug", r"\b(bugs?|errors?|fail(s|ed|ing|ure)?|broken|crash(es|ed|ing)?|exceptions?|regressions?)\b"),
           ("review", r"\b(review|pull request|pr)\b"),
           ("research", r"\?\s*$|^\s*(what|which|how|why|who|when|where|does|do|is|are|can|should)\b"))


def strip_name(content, name=NAME):
    """The text after a leading 'Tinker Flow' or '@Tinker Flow', or all of it."""
    return re.sub(rf"^\s*@?{re.escape(name)}\b[\s:,-]*", "", content.strip(), flags=re.I)


def parse(content, name=NAME):
    """'@Tinker Flow story: add X' -> ('story', 'add X'); no command -> ('help', '')."""
    # A command word ends at a space, a colon, sentence punctuation or the end: "Bug's", "Bug-free" and "Review/x" are
    # words, not commands.
    match = re.match(r"([A-Za-z]+)(?=[\s:,.!?]|$)[\s:,-]*(.*)", strip_name(content, name), re.S)
    return (match.group(1).lower(), match.group(2).strip()) if match else ("help", "")


def guess(request, flows):
    """The flow a request most likely wants."""
    for name, pattern in GUESSES:
        if name in flows and re.search(pattern, request, re.I):
            return name
    return "story" if "story" in flows else next(iter(flows))


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
    def __init__(self, client, owner, me, agents, channels, flows, home=None, poll=10, step_timeout=3600,
                 pickup_timeout=300, sleep=time.sleep, now=time.time, log=print):
        self.client, self.owner, self.me, self.agents = client, owner, me, agents
        self.channels, self.flows, self.home, self.poll = channels, flows, home, poll
        self.step_timeout, self.pickup_timeout = step_timeout, pickup_timeout
        self.sleep, self.now, self.log = sleep, now, log
        # One watermark per channel: a newer event in one channel must never hide an older request in another.
        self.since, self.seen, self.pending = {channel: int(now()) for channel in channels}, set(), {}

    def prime(self):
        """At start, take what the channels already hold as seen, so a restart never runs a recent request again.

        A snapshot rather than a timestamp cut, since Desktop's clock and Docker's can differ; the price is that a
        message posted in the seconds before this fetch, before "flow ready", is taken as seen too."""
        for channel in self.channels:
            for event in self.client.messages(channel, self.since[channel] - OVERLAP):
                self.seen.add(event["id"])

    def poll_once(self):
        """Handle every new message from the owner, oldest first, channel by channel."""
        for channel in self.channels:
            events = sorted(self.client.messages(channel, self.since[channel] - OVERLAP), key=lambda e: e["created_at"])
            for event in events:
                self.since[channel] = max(self.since[channel], event["created_at"])
                if event["id"] in self.seen:
                    continue
                self.seen.add(event["id"])
                if event["pubkey"] == self.owner:
                    self.handle(channel, event)

    def handle(self, channel, event):
        """A new message in #flows, or one that names Tinker Flow, runs a flow or gets a suggestion or the help."""
        root, text, addressed = root_of(event), strip_name(event["content"]), self.addressed(event)
        word = text.lower().rstrip(".!")
        if root != event["id"]:  # a reply: it answers a suggestion, or it is conversation
            suggestion = self.pending.get(root)
            # Outside #flows an untagged reply is for that channel's own agent, so only an addressed one counts.
            if suggestion and (addressed or channel == self.home) and (word in GO or word in self.flows):
                self.run(suggestion["flow"] if word in GO else word, suggestion["request"], channel, root,
                         event["created_at"])
                return
            if not addressed:
                return
        elif not addressed and (channel != self.home or not text or event["content"].lstrip()[:1] in ("@", "!") or
                                any("@" + agent["name"] in event["content"] for agent in self.agents.values())):
            return  # outside #flows only a message that names Tinker Flow is a request; one to an agent is theirs
        if word in GO:  # a `go` that no suggestion waits for, as after a restart, is never a request of its own
            self.say(channel, root, "Nothing here is waiting for `go`, maybe because I restarted: send your request "
                                    "again.")
            return
        name, request = parse(event["content"])
        if name == "stop" and (root != event["id"] or word == "stop"):
            return  # a stop only matters while its flow runs
        if name in self.flows and request:
            self.run(name, request, channel, root, event["created_at"])
        elif name in self.flows or word in ("", "help"):
            self.say(channel, root, self.help())
        else:
            self.suggest(channel, root, text)

    def addressed(self, event):
        """Tinker Flow's mention tag, or text that starts with '@Tinker Flow': pasted text carries no tag."""
        return mentions(event, self.me) or bool(re.match(rf"\s*@{re.escape(NAME)}\b", event["content"], re.I))

    def stops(self, event):
        """'@Tinker Flow stop', or a reply that says only 'stop'."""
        if self.addressed(event):
            return parse(event["content"])[0] == "stop"
        return event["content"].strip().lower().rstrip(".!") == "stop"

    def stopped(self, thread, asked):
        """Whether the owner stopped this flow in its thread since they asked for it."""
        return any(e["pubkey"] == self.owner and e["created_at"] >= asked and self.stops(e) for e in thread)

    def prefix(self, channel):
        """How the owner answers Tinker Flow here: untagged in #flows; elsewhere the channel's agent would take it."""
        return "" if channel == self.home else f"@{NAME} "

    def suggest(self, channel, root, request):
        name, lead = guess(request, self.flows), self.prefix(channel)
        self.pending[root] = {"flow": name, "request": request}
        others = ", ".join(f"`{lead}{other}`" for other in self.flows if other != name)
        shown = inert(" ".join(request.replace("`", "").split()))  # what would run, on one line, never a mention
        shown = shown if len(shown) <= 60 else shown[:60] + "…"
        self.say(channel, root, f"\"{shown}\" looks like a {name} flow: {self.flows[name]['about']}. Reply "
                                f"`{lead}go` to run it, or {others} for another flow.", notify=True)

    def help(self):
        lines = [f"- `{name} <request>`: {flow['about']}" for name, flow in self.flows.items()]
        return ("Tinker Flow runs a fixed sequence of agents for you, in one thread:\n" + "\n".join(lines) +
                "\n\nIn #flows just write your request: start it with a flow's name, or I suggest one and you reply "
                "`go`; reply `stop` in a flow's thread to stop it. In another channel, start with "
                "`@Tinker Flow story <request>` and answer me with `@Tinker Flow go` or `@Tinker Flow stop`.")

    def say(self, channel, root, text, notify=False):
        return self.client.send(channel, root, text, [self.owner] if notify else [])

    def run(self, name, request, channel, root, asked):
        """Run a flow in the owner's thread; a stop the owner sends from `asked` (the request's time) on ends it."""
        self.pending.pop(root, None)  # a thread runs one flow; a later `go` there starts nothing
        steps, started = self.flows[name]["steps"], self.now()
        context = {"request": inert(request), "topic": topic(request)}
        chain = " → ".join(self.agents[role]["name"] for role, _ in steps)
        self.log(f"flow {name} started in {channel} thread {root[:8]}: {chain}")
        self.say(channel, root, f"▶️ {name} flow: {chain}. To stop it, reply `{self.prefix(channel)}stop` here.")
        for role, template in steps:
            agent = self.agents[role]
            if self.stopped(self.client.thread(channel, root), asked):  # before the step, not only while it runs
                status = "stopped by you"
            else:
                prompt = self.client.send(channel, root, f"@{agent['name']} {render(template, context)}",
                                          [agent["hex"]])
                status, report = self.wait(channel, root, prompt, agent["hex"], asked)
            self.log(f"flow {name} step {role}: {status}")
            if status != "done":
                self.say(channel, root, f"⏹️ {name} flow stopped at {agent['name']}: {status}.", notify=True)
                return
            context[role] = quote(report)
        minutes = max(1, round((self.now() - started) / 60))
        take = f" Take the work to your PC: `Copy-AgentWork {context['topic']}`." if any(
            "/work/{topic}" in template for _, template in steps) else ""
        self.say(channel, root, f"✅ {name} flow done in {minutes} min: {chain}.{take}", notify=True)

    def wait(self, channel, root, prompt, agent, asked):
        """('done', the agent's last reply), or (why it stopped, None)."""
        start, picked, quiet = self.now(), False, 0
        while True:
            self.sleep(self.poll)
            thread = self.client.thread(channel, root)
            if self.stopped(thread, asked):
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
                home=env.get("FLOW_HOME") or None, poll=int(env.get("FLOW_POLL", "10")),
                step_timeout=int(env.get("FLOW_STEP_TIMEOUT", "3600")))
    flow.prime()  # proves the relay, the key and the membership first
    print(f"flow ready: {len(flows)} flows, {len(flow.channels)} channels", flush=True)
    while True:
        try:
            flow.poll_once()
        except Exception as error:  # a relay hiccup must not end the conductor; report and keep polling
            print(f"flow poll failed: {error}", file=sys.stderr, flush=True)
        time.sleep(flow.poll)


if __name__ == "__main__":
    main()
