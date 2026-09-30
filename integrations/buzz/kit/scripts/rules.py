"""One agent's buzz-acp subscription rules (BUZZ_ACP_SUBSCRIBE=config); agent.sh writes them before buzz-acp starts,
and buzz-acp reads them once.

buzz-acp takes the first rule that matches an event. The first keeps what every agent did before: a mention of it
in any kit channel. The second lets the owner write in the agent's home channel without a mention: only the owner's
own words, so never Tinker Flow's steps or another agent; never a message that starts with @ (addressed to
someone) or ! (an owner command); and never one that mentions an agent anywhere, since every kit agent's name
starts with "Tinker": that message goes to the agents it mentions, so one message never reaches two of them. The
author gate (BUZZ_ACP_RESPOND_TO) runs before any rule, so no rule widens who may give an agent a task.
"""
import os
import re
import sys

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")  # buzz-acp compares them as text
HEX = re.compile(r"[0-9a-f]{64}")
MENTION_KINDS = [9, 46010, 40007]  # buzz-acp's own for mentions: a message, a workflow approval, a reminder


def rules(channels, home, owner):
    if not channels or not all(UUID.fullmatch(c) for c in channels):
        raise ValueError(f"KIT_CHANNELS must be lowercase channel UUIDs, comma-separated: {channels}")
    if not HEX.fullmatch(owner):
        raise ValueError("BUZZ_ACP_AGENT_OWNER must be the owner's public key in 64 lowercase hex digits")
    listed = ", ".join(f'"{c}"' for c in channels)
    text = ('[[rules]]\nname = "mention"\nprompt_tag = "@mention"\n'
            f"channels = [{listed}]\nkinds = {MENTION_KINDS}\nrequire_mention = true\n")
    if home:
        if home not in channels:
            raise ValueError(f"KIT_HOME_CHANNEL is not one of KIT_CHANNELS: {home}")
        text += ('\n[[rules]]\nname = "home"\nprompt_tag = "home"\n'
                 f'channels = ["{home}"]\nkinds = [9]\nrequire_mention = false\n'
                 f"filter = 'author == \"{owner}\" && !(str_starts_with(content, \"@\"))"
                 " && !(str_starts_with(content, \"!\")) && !(str_contains(content, \"@Tinker\"))'\n")
    return text


def main():
    env = os.environ
    try:
        text = rules([c for c in env.get("KIT_CHANNELS", "").split(",") if c], env.get("KIT_HOME_CHANNEL", ""),
                     env.get("BUZZ_ACP_AGENT_OWNER", ""))
    except ValueError as error:
        sys.exit(f"rules.py: {error}")
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
