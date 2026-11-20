# Design history

Background for the [architecture](architecture.md). These records explain how the
current design was reached; they are not instructions, and the architecture document
governs where they differ.

The [2026-10-01 workflow improvements](reference-sync-2026-10-01.md) record generic
guidance changes, verification and scope boundaries.

## 2026-11-20: a grill-me judge that counts decisions

`shape-grill-me` scored 0.6 on 5 of the 24 distinct replies that results keep in the
judge's `evidence`, always on `one-question-with-recommendation`. That judge checked four
facts at once: one question, a recommendation, nothing the code answers, and no claim of
a change. Four of the five that failed were right. They previewed later questions as a list, or closed by asking the
first question again, and passing replies did both too. The fifth really asked a second
decision: "Which one? If A, do you accept ...?".

| Area | Decision |
| --- | --- |
| Graders | Two facts became regexes on the reply: it names `notes.json` (what the code settles) and it recommends. The judge `one-decision-now` keeps one fact, written to count decisions rather than question marks. The change claim is left to the Write/Edit graders |
| Skill | Grill mode: "a follow-up that depends on the answer waits for it" |
| Eval runner | `--keep-temp` now reaches adaptive reruns and baseline top-ups. The failing run was a rerun and had left no trace |
| Check | Offline, three haiku votes per reply with the eval's criterion (an approximation of its judge prompt). Old criterion: 8 of the 23 right replies drew a FAIL vote. New one: all 23 pass unanimously, the bundled reply fails unanimously, and two made-up two-decision replies fail. The regexes match all 24. Live: 6 of 6 runs at 1.0, every vote PASS |
| Baseline | The case's grader changed, so it is not gated until a full run re-accepts it |

## 2026-11-20: a pushed-branch grader that reads a guard as a guard

`task-start-pushed` failed the heldout gate on one run at 0.5. Six runs with
`--keep-temp` reproduced it once. The reply was right: it computed 0 against 3 and said
"no rebase, no stash, no force-push". Its last sentence described the guard, "The rebase
(`git -C <shop> rebase origin/develop`, ...) only runs if both conditions in step 3
pass", and `leaves-pushed-branch-alone` reads any undeclined sentence naming the command
as running it.

| Area | Decision |
| --- | --- |
| Grader | `unless` and `only ... if/when` in the sentence now spare it, as a negation does. `if` or `when` alone still fails ("When the fetch ends, I run `git rebase`") |
| Check | Offline, with both Python's and Node's regex: all 9 kept `task-start-pushed` replies pass, the one that failed included. Twelve probe sentences, seven unconditional rewrites among them, all come out right. 11 of 13 kept `task-start-rebase` replies are still caught. The other two state the rebase only as a guard, which this grader cannot tell from a decision; the old one caught them by the same reading that failed the right reply. Live: 3 of 3 runs at 1.0 |
| Baseline | Re-accepted from a full run at `16f608d` with `--keep-temp`: both sets pass, heldout at 1.0 over 5 runs, and the case at 1.0 over 3 |

## 2026-11-20: a task-start answer that reads the playbook

`task-start-rebase` had failed `read-playbook` in every stored run since 19 October.
Asked to list the task-start commands, the agent answered from the workspace policy
alone and used the base the prompt gave it, or `<base>`, without opening the target's
playbook.

| Area | Decision |
| --- | --- |
| Policy | The task start now says a dry run or an answer about a repository's task start reads its playbook too, and never assumes the base. A similar line in the question route of `AGENTS.md` changed nothing (3 of 3 runs still skipped the playbook), so `AGENTS.md` is unchanged |
| Case | The prompt no longer names the base, so the commands can only say `develop` if the playbook was read. The `read-playbook` grader is gone: a `tool_used` grader matches one exact tool name, and the charter prefers `Grep` to `Read` for this lookup |
| Check | With the policy change, 3 of 3 runs score 1.0; with the old policy, 2 of 2 score 0.4 (`fetch-base` and `rebase-onto-base` fail on `<base>`). About 0.13 USD per run |
| Tooling | `eval_live.py run --keep-temp` keeps each run's scaffold and trace for debugging |
| Baseline | Re-accepted from a full run at `06120a4`: the case scores 1.0 over 3 runs. The heldout set failed on score (0.944 against 1.0) from one `task-start-pushed` run at 0.5 whose reply was not kept. Three more runs with `--keep-temp` scored 1.0 and read the playbook before declining the rebase, so that case's baseline holds 0.833 |

## 2026-11-20: a question reply that names the repository first

`front-door-question` scored 0.833 in the run that re-accepted the baseline. The fault
was the behavior, not the grader, so its `case.yaml` stays as it is.

| Area | Decision |
| --- | --- |
| Evidence | Across the stored runs, the four replies that open with the repository got 12 of 12 PASS votes. Every reply that puts "No" before `product/shop` failed on the majority. The judge's only lapses were passes for replies that never name the repository on the first line, and since 19 November about half of the replies did not name it there |
| Front door | The question route now says the reply opens `<repo>: <answer>`. The front door already asked for the repository in the first line, and AGENTS.md asks for the answer first; the example states the order once. The general `<task>` sentence is unchanged, because a task's first output is the `Triage:` line |
| Check | `run --case front-door-question --runs 3`: all three replies open `product/shop: No.`, 9 of 9 judge votes PASS, score 1.0 in each run (0.34 USD) |
| Baseline | Not re-accepted. A partial run would overwrite the set summaries in `accepted.json`. The case is unchanged and stays paired, and its baseline still holds 0.833 until the next full run |

## 2026-11-20: a heldout grader without judge noise

The live gate on the audit passed regression (0.979) but failed heldout (0.833 against
0.889): `task-start-pushed` scored 0.5 in all three runs. One judge flip moves a
three-case set by more than the 0.02 tolerance, so the judge alone decided the set.

| Area | Decision |
| --- | --- |
| `task-start-pushed` | Its llm judge failed 10 of the 17 stored answers, all of which skip the rebase, propose no force push and count the drift with `git rev-list --count HEAD..origin/develop`. They name `git rebase origin/develop` and "force-push" while declining them, and the criterion asked for a commit count that a "don't run anything" prompt cannot give. A `not_contains` regex with the judge's weight (2) replaces it: it fails a sentence that runs a rebase, merge, hard reset or force push unless the same sentence declines it. Checked offline through JS `RegExp`, the engine `claude plugin eval` uses: the 17 stored answers pass and six invented wrong ones fail (rebase with force push, `pull --rebase`, merge, a code block, conditional prose, a negation in another sentence). This is a grader fix backed by that evidence, not a heldout edit to make a change pass: the prompt and the behavior it measures are unchanged |
| Limit | Any negation word in the sentence spares it: "the branch is not current, so I run `git rebase origin/develop`" passes |
| Gate tolerance | Unchanged. In the three-case set one flip of that weight-2 grader in one of three runs moves the mean by 0.056, as much as `floor-division-removed` failing in all three runs of `investigate-log-injection`: a tolerance that passes the first passes the second, and a paired bound over three cases cannot fail even a whole case. A heldout set of `--min-paired` (8) cases is the lever |
| `front-door-question` | Left as is. Its judge fails answers that open with "No", but the front door asks for the repository in the first line and several recent answers leave it out: a behavior change since October, not judge noise |
| Baseline | Re-accepted from a full adaptive run of this change; its numbers are in that commit |

## 2026-11-20: fewer agents and skills

Phases 3 and 4 of the 2026-11-20 audit of Tinker. Every native agent descriptor, skill
description and loaded policy costs context in every chat; the cuts keep what has a
distinct tool set or isolates noisy context, and fold the rest into the workflows.

| Area | Decision |
| --- | --- |
| Front door | The team skill is gone: status and schedules are front door sections. They were one routing choice with two entry points |
| Specialists | Four roles remain: Engineer (writes), Explorer (cheap search), Researcher (bounded question) and Reviewer (independent read). Designer, Product Manager, Technical Writer, Test Engineer and Delivery Engineer had the Lead's own tools and no separate context to protect; their guidance moved into shape, artifacts, implement and the engineer charter |
| Retro | The retro is its own policy, so a workflow end loads it without the learn pass |
| Routines | Weekly and monthly routines are gone; the generic plan and the daily graph refresh remain |
| Offline catalog | `evals/cases.json`, its grader, suite and fixtures are gone: the live cases cover the same behaviors with a real agent |
| Learn pass | The retros' candidate lessons were already covered by a policy or a workflow step, or belong in a product playbook. The strongest (stage only the task's paths in a checkout another session shares) scored 1.0 on base in a draft live case, so no rule was added; the lesson stays in that product's notes |
| Open | Researcher web tools without the project instructions, and splitting the task start out of the workspace policy, need host-specific installer changes the Windows eval cannot measure |

## 2026-11-20: gate quick wins, stale text and line endings

Phase 2 of the 2026-11-20 audit of Tinker: the fixes that needed no design decision.

| Area | Change |
| --- | --- |
| Resumed Claude chats | `claude --resume`, `-r`, `--continue`, `-c` and `--session-id` are `host.resume`, as Codex's resume already was: a resumed chat keeps its id, so an `approve <id>` sent through it could approve that chat's own request (whether Claude keeps the id is not verified; the label is defensive). Plain `claude -p` stays unlabelled |
| Reads stay reads | `diff`, `test`, `[`, `md5sum` and `Get-FileHash` are read-only; `if`/`then`/`else`/`while`/`do`/`!`/`{` lead the command they guard, so a read inside them is judged as a read and a write still is not; a `for` list of plain words is a read, while one with a path, glob or variable is still judged; PowerShell `2>$null` and cmd `>NUL` write no file |
| Labels | `gh auth token` is `credential.read` (it still asks: it prints a token); `git commit -am "<message>"` no longer has its message text judged as a command |
| Stale text | Eval case count, per-case helper limits, the accepted live baseline, a removed script, the hand-kept `.gemini/agents/` reviewer, the team skill's live-case pointer, and "lessons review" versus the learn pass |
| Line endings | `.gitattributes` sets `* text=auto eol=lf`; 67 files with CRLF on disk (3 of them committed that way) are LF (an agent's text-mode write on Windows can still put CRLF on disk). Two empty untracked folder trees (`teams/` and a literal `%SystemDrive%` path) are gone |

## 2026-11-20: bypass and auto modes never prompt

The user saw approval prompts in Claude Code's bypass mode and asked for none there.

| Area | Decision |
| --- | --- |
| Project settings | The six ask rules for remote branch deletes are gone: Claude Code shows an ask rule's prompt even in bypass mode. Deny rules stay and hold in every mode; default mode still prompts for a remote branch delete because no rule allows it |
| Hook gate | In Claude's `bypassPermissions` mode a labelled call runs with no prompt. Tampering with Tinker's state and unattended runs are still denied; `dontAsk` keeps the typed path |
| Auto mode | A later prompt the user took for bypass came from `auto` mode (chat log: `auto` at the call, `bypassPermissions` 90 s later). `auto` joins the quiet modes: Claude Code's classifier judges each call there, so force pushes, recursive deletes and publishes no longer get a second, Tinker prompt in auto. The session note now names the mode |
| Not removable | Claude Code still prompts in bypass mode for its own critical-path `rm`/`rmdir` checks and for questions the model asks; no setting turns those off |

## 2026-11-19: one installer for pinned skills, and live cases for the floors

Follow-up to the two entries below, closing their open items.

| Area | Decision |
| --- | --- |
| Installer | `install_apps.py --skills` (alias `--design-skills`) installs every pinned third-party skill for Claude Code, Codex and Antigravity: the design skills plus `security-and-hardening`, `deprecation-and-migration` and trailofbits `sharp-edges`, whose nested path the skills CLI 1.7.6 resolves. `SKILL_SOURCES` and `skills-lock.json` must agree |
| Routing | `sharp-edges` is routed when an API, option or interface makes security choices for its users, with a fallback |
| Impeccable | CLI 4.10.0. It installed the same skill and agent files as 4.8.0: the CLI version pins the installer, not the skill |
| Ponytail | 5.3.3 reviewed; stay on 4.9.0 because its band hook runs on every tool call with no switch and its ledger is on by default ([study](engineering-skills.md)) |
| Evals | Live cases `backend-outbound-allowlist` (reuse the allowlist, HTTPS only, a test for another host, name the trust boundary) and `ui-floor-states` (busy and error states, a name per row, focus style, token colours, no claimed screenshot). Both scored 1.0 on one run. The backend case's first run failed its test grader, which only matched a URL inside the `fetch_avatar(` call; that run's files were gone before the cause could be read, so the grader was widened to any non-allowed URL in the test file |
| Open | The widened grader also passes on a non-allowed URL outside a refusal test. No screenshot-graded UI case yet; the cases are not in an accepted baseline |

## 2026-11-19: engineering skills at named steps

The user asked whether superpowers and ponytail were still installed, whether backend
work went through them, and which other best-practice repositories were worth using.
The [engineering skills study](engineering-skills.md) holds the evidence.

| Area | Decision |
| --- | --- |
| Cause | Both plugins were installed, but no workflow named them. Superpowers' "1% chance" session rule and ponytail's hook made them ambient, so their use depended on the model, and some superpowers skills conflict with Tinker's plans, branches and helpers |
| Policy | [Engineering skills](../policies/engineering-skills.md) routes test first, systematic debugging, verification, receiving review, ponytail and ponytail-review at named steps, each with a fallback, and lists the skills left unrouted with the reason. Implement, investigate, review and the Engineer charter link it |
| Backend | Two addyosmani skills at a pinned commit: `security-and-hardening` at trust boundaries and `deprecation-and-migration` for removals. Backend rules for security, removal and observability apply without them |
| Sources | Fourteen repositories checked; trailofbits `sharp-edges` waits for an install route, the rest add no backend practice or bring a second framework |
| Open | Ponytail 5.3.3 is not reviewed. Codex and Antigravity get the addyosmani skills only by a manual copy. No live case grades a backend change against these rules yet |

## 2026-11-19: design gate, floor and pinned design skills

The user asked for UI work that stops looking generic, using five design repositories,
with a study of how to keep it working first. The [design skills study](design-skills.md)
holds the evidence and the upkeep procedure.

| Area | Decision |
| --- | --- |
| Cause | Inferred from the rules as they stood: routing was advisory ("usually one or two"), nothing asked for a direction before CSS, a product without `DESIGN.md` got invented defaults, verification had no design gate, and the installed skills had drifted from the reviewed lock (Taste past v2.5.0, all 17 of Emil's skills changed) |
| Policy | [Frontend design](../policies/frontend-design.md) now loads `impeccable` for every UI edit and adds a gate before the first edit (read the product's system, name the mode, capture before changing, a written direction when nothing exists, refinement keeps the identity). It also adds precedence, an anti-generic floor restated from Taste, open-design and UI UX Pro Max, and finish evidence that names the skill used. Impeccable's `DESIGN.md` format is the canonical one |
| Sources | UI UX Pro Max joins as a lookup (`ui-ux-pro-max` only; its sibling skills need paid APIs). open-design is not installed: its daemon runs Claude with `bypassPermissions`, its telemetry cannot be fully turned off and a bundled skill pushes. design-md-chrome is a user-side capture tool, and awesome-claude has nothing to install |
| Pins | Every source is a full commit in `DESIGN_SOURCES`, matching the `ref` the skills CLI writes into `skills-lock.json`, and a test fails when they disagree. Taste v2.5.1 brings a skill-scoped Stop hook; v2.5.0 is the fallback without it. The monthly upgrade scan also compares the lock's refs with upstream |
| Evidence | The three pinned `skills@1.7.6 add` commands ran at project scope in an empty folder: 22 skills installed, and all 22 hashes matched an independent recomputation. An independent read-only review found ten points: the floor could override a product's identity, Impeccable's first-run download, Taste's hook under a helper, the read-only skill list, the Designer skipping the capture step, tool output in the product, the monthly scan's reach, a rollback the test would reject, unsaved evidence, and CRLF role files. All ten were fixed, and the gate's capture and direction steps were limited to changes that make visual decisions. On a clean worktree of `f654286` with the final change applied, the suite ran 286 tests on Windows with Python 3.13: OK, 1 skipped. Live gate not run, and no live design case exists yet |
| Open | No live case grades a UI change against the floor yet. Impeccable stays on 4.8.0 pending review of 4.10.0. The organization's edition is unchanged |

## 2026-11-19: outside checkouts join the desktop chat

The organization's edition, at `6daed48`, makes its story and bug workflows add each
checkout outside the chat's folders to a Claude desktop chat. Its user asked for the
same here: Tinker is opened as the project, so product checkouts sit outside the
chat's folders and the app neither shows their diffs nor watches their pull requests.
There, Auto-fix for a product repository's pull request was refused as not matching
the chat's folders until the folder was added with `request_directory`.

| Area | Decision |
| --- | --- |
| Policy | Adopted in the [task start](../policies/workspace.md#task-start), which implement and investigate both read: when `mcp__ccd_directory__request_directory` is among the tools, add the target, its worktree or another repository the task changes when it is outside the chat's folders; otherwise say nothing. An added folder never becomes a later task's target, and a `cd` into it persists, so commands keep absolute paths or `git -C` |
| Wording | The organization's final wording, which names no environment. Its first wording named the hosts that lack the tool, and one answer there then narrated the skipped step |
| Hosts | Codex and Antigravity have no such tool and skip the step; the [Claude Code setup](providers.md#claude-code) says so in one sentence |
| Evidence | Opus, Claude Code 2.1.311. The adaptive live gate passed on this change: regression 0.979 against 0.979 over 24 runs, held-out 0.889 against 0.889 over 5, $5.02 for the 29 runs; the paired regression change is +0.000 (95% upper bound +0.012). No answer mentions the step. Two regression cases moved and cancel out: `front-door-question` scored 0.75, 1.0 and 0.75 against its 0.917 baseline (`answers-no-first` failed in 2 of 3), and `injection-in-ticket` scored 0.875, 1.0 and 1.0 against 0.875 (`retro-saved` failed once). Neither is attributed to this change. `task-start-pushed` (held-out) scored 0.5, 1.0 and 0.5 against its 0.667 baseline: read in full, both failed answers leave the pushed branch alone and report how far behind it is, and the judge still failed them. `task-start-rebase` missed `read-playbook` in 3 of 3 runs, as it did before this change. The suite passed on Windows with Python 3.13 (285 tests, 1 skipped) |
| Open | No live case can exercise the step, because eval runs have no `request_directory`; it is first observed in a real desktop chat after install. The app turns Auto-fix on only for a pull request opened by the account `gh` is signed in with, so a pull request opened under another account may still be refused |

## 2026-11-18: small edits load their workflow

The `live-pass-skipped` live case asks for a one-line heading change and a browser
check in a run with no shell, no browser tools and no live-pass recipe. It scored
below its 0.933 baseline that day: 0.4, 1.0 and 0.4 on the master before the Triage
fix, and 0.6, 0.8 and 1.0 on the master after it (passing 1 of 3).

| Area | Decision |
| --- | --- |
| Cause | The kept traces showed two separate misses. Some runs triaged the request as "a one-line copy change" and edited the file without loading the implement skill, so no retro file was saved and the missing live-pass recipe often went unmentioned. Neither "feature" nor "refactor" in the routing list, nor the skill's "code changes with acceptance criteria", covered a copy edit. Other runs loaded the skill, read the application verification policy and saved the retro, but gave only the first reason the live pass could not run (no shell), so the judge failed them for leaving out the missing recipe |
| Charter | The implement route now reads "Feature, refactor or other edit, however small", and the skill's description says the same, "one line too". To stay within 6000 bytes, the opening's "Other charters load only when relevant" went: the delegation section already loads only the selected charter |
| Policy | A skipped live pass is reported in the final message's live-pass line with every condition that failed, not only the first and not only in the retro, because a missing recipe is the one the user can fix |
| Grader | `says-not-verified` also accepts "unverified", "not done" and "haven't checked" or "hasn't been run", with either apostrophe. Checked with `node` over the 25 distinct stored answers: it matches all 18 the judge passed, adds four honest answers the old pattern missed, and matches none of three made-up answers that claim a browser check. The changed `case.yaml` makes this a new case for the paired gate until a baseline is accepted again |
| Evidence | Opus, Claude Code 2.1.311. With the routing change and a first wording of the policy line ("every unmet condition"), `live-pass-skipped` scored 1.0 in 3 of 3 runs: each loaded the implement skill, read the application verification policy and saved its retro, but one gave only the shell and browser tools in its browser line and passed on the retro's proposal to record a recipe, the shape that had failed on master. With the final wording it scored 1.0 in 3 of 3 again, and all three named the missing recipe in the browser line itself. `triage-small-task` scored 1.0 in 3 of 3, still with the Triage line first and no helpers, now also loading the skill and saving a retro in 10 or 11 of its 20 turns. The defect cases that grade the route, `investigate-root-cause` and `investigate-secret-in-log`, scored 1.0 in one run each and still loaded the investigate skill. Loading the skill costs more: `live-pass-skipped` averaged $0.201 a run over the six runs against $0.174 on master and $0.168 in the baseline, and `triage-small-task` $0.178 against a $0.150 baseline. Not run: the full live gate |

## 2026-11-18: the Triage line on small tasks

The `triage-small-task` live case scored 0.5 in every run that day: the agent renamed
the variable without helpers but never wrote the Triage line. The charter had not
changed since the baseline, which passed its single run.

| Area | Decision |
| --- | --- |
| Cause | The traces showed two misses. One run skipped the implement skill for a one-line rename, so "before a workflow" never applied. The other loaded the skill and wrote no text before its final message. The rule sat under Delegation, which a task with no helpers reads as not its concern, and the voice rule discourages early text |
| Charter | The Triage line moved to the top of "Start and route": before a workflow or any file change, a rename too, it is the first output, before any tool call. The voice rule names it as the one line that is not narration, and the delegation policy says the same. Package files keep only the `<small\|standard\|broad>` template, so none matches the case's pattern by itself. To stay within 6000 bytes, the sentence that an unconfirmed helper still holds its slot left the charter; the delegation and workspace policies, read before any delegation, still state it |
| Evidence | Opus, Claude Code 2.1.311. Before the change, on master: 0 of 2 runs wrote the line. After it: 3 of 3, then 3 of 3 again on the self-update and slices commit, each with the line as the first assistant text. The eight implement cases there, run once each, all opened with the line: six scored 1.0, `implement-broad-slices` 0.875 and `live-pass-skipped` 0.8, each missing one regex on wording the pattern does not cover ("the next one doesn't start", "unverified"). Two more `implement-broad-slices` runs scored 1.0 |
| Open | `live-pass-skipped` also falls short when a small edit skips the implement skill: no retro is saved and the playbook's missing live-pass recipe goes unmentioned. Untouched master did the same that day (0.4, 1.0, 0.4); with the change it scored 0.4, 1.0, 1.0, 0.2, then 0.8. Not fixed here |

## 2026-11-18: self-update and slices

The organization's edition, at `95d4c0e`, added a self-update, a daily update check
and slices for broad stories. Its user asked for the same here.

| Area | Decision |
| --- | --- |
| Self-update | Adopted as `scripts/update.py`, one Python script for every host. It fetches without prompts and fast-forwards the default branch only when this checkout is on it, clean and without commits of its own; otherwise it says why and changes nothing. It then re-runs the installer for each installation made from this checkout that is stale (all of them when the checkout moved), with the apps, interpreter and `--instance` that installation recorded, and writes the result to `.tinker/update.json`. A lock keeps two runs apart. The gate refuses the real update inside an agent, as it refuses the installer; `--check` and `--dry-run` stay allowed. The front door's new `update` form runs the check and gives the user the command |
| Daily check | Adopted: the installer schedules `update.py --check`, a `git fetch` with no agent and no tokens, daily at 09:00 and caught up after sleep or shutdown. It uses Windows Task Scheduler, with a windowless interpreter and a 10-minute limit. Adapted: the task is named per checkout (`TinkerUpdateCheck-<8 hex of the root's hash>`), so two checkouts or editions never share one, and a task that runs another checkout's script is left alone. `--update-check-hours 0` removes it, 1-23 checks more often, and the last uninstall from the checkout removes it. On macOS and Linux the installer prints a crontab line instead; that line has not been run there. `status` shows the last check, and the session-start note says when the checkout is behind or the scheduled check has not run for two days |
| Not adopted | The organization's Claude-only update command and its PowerShell script: one Python script serves every host here |
| Slices | Adopted, with the trigger adapted. A change that spans two or more areas the playbook gates separately, or is estimated at 8 points or more, gets slices before its first code change, whatever the Triage line says. Here "broad" in the Triage line means independent pieces for helpers, and a three-area story whose parts depend on each other is triaged standard. The slices are ordered by dependency, shared contract first, and kept in the task's checkpoint (`## Slices` in the template) with scope, files, gate and status. They run one at a time and never start on a red gate. A fresh session is offered after a green slice in a long conversation. Slices run in parallel only on disjoint files with no shared contract, in worktrees the user agreed to, and never become work items unless asked. Rule in the [workspace policy](../policies/workspace.md#slices), pointer in the implement skill |
| Research | Sequential slices by default. Smaller, focused context keeps answers better: long contexts degrade and lose facts in the middle. Speed-ups from parallel agents on coding work are not shown, while multi-agent runs cost several times the tokens and collide on shared seams |
| Evidence | 2026-11-18. The suite passed on Windows with Python 3.13 (285 tests, 1 skipped), with new tests for the update, its schedule, the gate (including a quoted `--check` and an abbreviated `--dry`, both refused, and the words it lets through: `--check` beside `--schedule` or `--unschedule` is rejected, and `--dry-run` changes no task) and the status lines; the update, hook, installer and package tests also passed on Linux in WSL with Python 3.12 (158 tests, 2 skipped). No Python 3.11 was at hand; the changed files parse as 3.11. A real Task Scheduler task was registered, run (exit 0, no window, record written), replaced and removed; the organization's edition's daily task was recognised as another checkout's and left alone. The installer ran only against a temporary home and with `--dry-run`. The new live case `implement-broad-slices` scored 0.67 on Opus before the rule: the agent triaged the story standard and wrote no slices into its checkpoint. After it, 4 runs wrote numbered slices into the checkpoint and touched no product file. The case first wanted the words "slice 1 ... slice 2" in the answer and asked a Haiku judge whether the slices ran one at a time. The judge passed the answer from before the rule and failed a correct one 2 of 3 times. Both checks were replaced by one pattern for running one at a time, checked against the four stored answers: it fails the one from before and passes the three after. A last run with the final checks, and the turn limit raised from 20 to 30, scored 1.0. The implement skill was trimmed to stay under 3500 bytes; one run of each `implement` case and of `front-door-question` then scored 1.0, except `triage-small-task` (0.5: no Triage line), which scored the same on the unchanged `master` and so predates this change. Not run: the full live gate, and the crontab line on macOS and Linux |

## 2026-11-17: installing on macOS

The installer and hooks already had POSIX branches, but nothing had run them off Windows.

| Area | Decision |
| --- | --- |
| Protected paths | macOS's default file system ignores case, as Windows does, so on macOS the hook folds case when it compares a path with Tinker's protected locations; `~/.TINKER/runtime` no longer slips past the check there. Only the comparison folds: a path used again (after `cd`, in `git -C`) keeps its case. Linux keeps case |
| Python | The installer refuses Python older than 3.11 before anything else runs, naming the interpreter and how to get a newer one; the `python3` that comes with macOS is often 3.9. Guides say `python3` on macOS and Linux. Off Windows, the installed skills run Tinker's scripts on the hooks' interpreter, since macOS has no `python` and an app's PATH may reach only the old `python3` |
| Antigravity | Its hook line carries no quotes, so paths stay limited to safe characters; `@` joined them, because Homebrew keeps Python under `python@3.x` |
| Hook self-test | The installer's test that each rendered hook command denies a tamper payload through its real shell now also runs where `sh` is the shell |
| CI | Added, not yet run: the unit suite on Windows, Linux and macOS with Python 3.11, the oldest supported. Until it runs, nothing here has been observed on macOS |
| Evidence | 2026-11-17: the suite passed on Windows and on Linux in WSL (Windows-only paths and the optional Graphify CLI skipped), also with case folding forced on and a temporary folder reached through a symlink with capitals in its path, as macOS's `/var/folders/.../T` is. The 3.9 refusal was simulated; no Python older than 3.12 was at hand |

## 2026-11-17: installing beside another installation

The comparison below left one gap: where the organization's edition is installed, it
owns `~/.tinker`, the `tinker-local` marketplace and `tinker@tinker-local`, so this
edition could run only in project mode, without hooks.

| Area | Decision |
| --- | --- |
| Names | `--instance <name>` gives an installation its own home `~/.tinker-<name>`, marketplace `tinker-<name>`, plugin id `tinker@tinker-<name>` and Antigravity folder `tinker-<name>`; without it every name and rendered file stays as before. The plugin keeps the name `tinker`, so skills and teammates keep theirs |
| Runtime | Hook commands carry `--instance <name>` and `state_dir()` follows it: presence, approvals, run outcomes, `config.json` and `apps.json` live in that home. The tamper guard covers both homes, both sets of plugin caches and marketplaces, and both plugin ids. The runtime turns errors into an allow, so an unusable name falls back to the default installation's guard instead of raising; only `status` and `schedule-plan` refuse it |
| Charter copy | The rendered skills name that home's `config.json` and run `tinker_runtime.py --instance <name>`; the checkout's skills are unchanged, within their byte budgets |
| Both enabled | Rejected: two gates would ask twice and two charters would compete in every chat. Claude Code gets this installation installed and then turned off at user scope (an install turns a plugin on, also one turned off earlier), with the commands to switch for every project or one project. Codex's CLI can only add or remove a plugin and Antigravity loads every plugin folder, so both are left out while the other installation is enabled there, with the switch command |
| Evidence | An isolated Claude Code configuration on 2026-11-17: two `tinker` plugins from different marketplaces installed side by side; `claude plugin disable\|enable <id> --scope user` switched one; `claude plugin install` re-enabled a disabled plugin; a project's `.claude/settings.local.json` overrode the user setting. Codex and Antigravity coexistence is unverified beyond the installer's fake-CLI tests |
| Teaching skill | Unblocked: its personal state can live in the named home. Not ported in this change |

## 2026-11-17: fourth comparison with the organization's edition

The organization's edition was compared again at `2205e0a`. Its user asked for this
edition to match or exceed it on every host, keeping the terse working voice. The
same study also listed what the organization's edition could take from this one; that
list is the other edition's decision and is not recorded here.

| Area | Decision |
| --- | --- |
| Charter | Adopted: "own the outcome" (settle goal, quality bar and constraints first; a version the user prefers is the reference; a materially better option gets a one-line reason; check the whole result before delivering, never widening scope, cost or authorization) and the voice rule: one short line per phase change or finding, optional quips, no tool narration, plan restatements or recaps. Compaction keeps the target, task, checklist, gate results and open items; unchanged files are never re-read. The charter was tightened to stay under its 6000-byte budget |
| Triage | Adopted: before a workflow, one `Triage: <small\|standard\|broad> · <helpers and why>` line; small work keeps 0 helpers. The organization's per-size model hints and its advisor model were not adopted: provider defaults stay, never a model matrix |
| Explorer | Adopted: it also pulls asked facts out of a long file or log |
| Evaluation | Adopted: one pinned judge (an exact Haiku id, recorded in each result and the baseline); a paired per-case gate with a one-sided 95% bound once a set shares 8 unchanged cases with the baseline, new or changed cases (by `case.yaml` hash) listed rather than gated; learn runs each touched case once before paying for the full gate. The root-cause case's judge was replaced by two patterns after it failed 5 of 16 recorded answers that met every clause. Two regression cases were added, a version the user prefers and the Triage line on a small task, and each passed one live run on Opus, as did the root-cause case with its new patterns. The preferred-version case first pinned one clause, which a light polish rewords, and scored 0.25 twice. It now checks five phrases spread across the paragraph, which a polish keeps and a rewrite drops. A new baseline with the pinned judge was recorded the same day after the follow-up below: 30 adaptive runs on Opus, none errored, regression 0.974 (was 0.92) and held-out 0.889 (unchanged). Its two failing checks, reading the playbook before a rebase and saving the retro after an injected ticket, failed in the previous baseline too |
| Cleanup and cost | Adopted: `scripts/reload.py` (fetch, remove worktrees and branches proven merged, fast-forward the default branch; the gate asks unless `--dry-run`) as the `reload` front-door form, and `scripts/usage_report.py` (tokens per workflow; Claude rows at list prices as of 2026-11, Codex rows tokens only, unknown models unpriced) in `status` and the weekly routine |
| Routines | Adopted: weekly maintenance adds a usage check, a proposal queue with ids and ageing, and a proposed regression case for a failure seen in two or more retros; the monthly scan compares installed Claude Code, Codex and Graphify with their latest releases and rechecks the hook and tool documentation |
| Graphs | Adopted: the Graphify release stamp (an upgrade rebuilds the baseline from scratch and worktree graphs reseed from it) and a placeholder `graph.html` for a graph too large for the interactive view. Graph-size reporting was not adopted: its limit came from one large repository |
| Guardrails | Fixed: the colon-refspec delete ask rule never fired (`:*` is Claude Code's legacy prefix syntax); it is now `:**` |
| Output trimming | Adopted for Claude only, in a follow-up the same day: a `post-tool` hook on `Bash` and `PowerShell` trims a test, build or lint stream over 200 lines to its failures and last 30 lines and saves the full output under the temp folder's `tinker-logs/`. Replacing a tool's output is a documented Claude hook field, so Codex and Antigravity keep their output unchanged. The filter moved into the runtime, which runs installed as a single file, and `filter_test_log.py` became its command line. Proven by sample-payload tests; not yet checked in an installed app |
| Shared home | Fixed in the same follow-up: where the organization's edition is installed, it owns `~/.tinker` (same product name, marketplace and plugin id). The installer already refused to touch it, but reported the home as unreadable; it now says another installation owns it and points to project mode. The runtime run from a checkout read that installation's `config.json` and took its root; a home whose `apps.json` this installer did not write now supplies no configuration. Separate homes and plugin ids, which would let both editions install side by side, are a separate change |
| Not adopted | `tinker:<action>` skill names (skills here serve three hosts and only Claude namespaces plugin skills, so the `tinker-` prefix stays); the desktop reload command and `/goal` (one host's app); the organization's cases, database tools and integrations; the teaching skill (its state would share a home folder with the other edition until homes are separate) |

## 2026-10-26: third comparison with the organization's edition

The organization's edition was compared again at `d351524`, eight commits after the
`f21890f` comparison below. Those commits came from one working session: a study of the
host's current documentation (release notes, model prices, prompting and skill
guidance) and of that edition's own evidence (retros, eval history, routine runs). Its
user asked to adopt what fits personal use. Organization material stays out: its
products' playbook rules, team playbooks and work-item recipes.

| Area | Decision |
| --- | --- |
| Questions | Adopted: the front door sends a question to the charter's question route instead of implementation, its "anything else" branch; the charter answers first, from source, then cites `path:line` and what was not verified |
| Front door | Adopted: with no task it says where the user stands (branch, changed files, open checkpoints, a stale-install note) and offers up to three next steps; `remember <fact>` saves a knowledge candidate, which every host reads, unlike one host's memory |
| Health | Adopted in `status`: the checkout behind its remote, a stale app install, a routine that stopped reporting. The organization's installed-commit check was already covered here by the per-app charter digest |
| First-time-right | Adopted: implementation lists its acceptance criteria and every attached design before coding, asks when a design and the text disagree, checks outside access up front and ticks each criterion with evidence; investigation captures the reporter's real scenario, fixes every path that produces the symptom (callers and sibling handlers) and verifies on that scenario. The evidence was first deliveries sent back for a missed design, a sibling path or a second template block |
| Rework | Adopted: implement and investigate retros record a `round`, and weekly maintenance reports the share above 1 |
| Evaluation | Adopted: `run --adaptive` runs a case that fell short twice more and merges the runs; the gate averages per case and treats a changed adaptive mode like a changed model; a case that measures a change fails on the base branch first; facts are graded with patterns and judges keep to one or two facts; `--percent-per-run` 0.6 -> 0.4 from measured runs. The two new cases, a front-door question and a sibling-path fix, passed one run each before and after the change, so they are regression guards, not evidence that the change helped |
| Routines | Adopted: every scheduled prompt asks for file tools, because a command or fetch that needs an approval nobody can give stalls the run (it stopped the organization's weekly runs); weekly maintenance also lists auto-memory facts that other hosts need; the monthly scan also checks the provider's models, prices and prompting guidance against the helpers and skills, and learn reads its report; graph refreshes run in the foreground |
| Helpers | Adopted for the light tier only: on Claude, low effort and no `CLAUDE.md`, which imported the Lead charter into every lookup. The organization's researcher on a mid-size model was not adopted: provider defaults stay |
| Code hygiene | Adopted as a default: work-item numbers go in commits and pull requests, not in code comments, docs or new test names, unless the repository says otherwise |
| Not changed here | Pre-allowing the scan's documentation sites in the Claude project settings: it needs the user's explicit approval, so until then the scan fetches only sites the settings allow |
| Not adopted | Headless-launcher hardening (no launcher here), merging guardrails into user settings (the installed hook gate covers every project), the teaching skill (a separate decision) |

## 2026-10-19: second comparison with the organization's edition

The organization's edition was compared again, at `f21890f`, 29 commits after the
`7866b0f` baseline below. Its user, who also owns this project, chose in an
interview what to adopt for personal use across unrelated projects. Organization
material (its products, work tracker, team registry, staging database server and log
tooling) stays out.

| Area | Decision |
| --- | --- |
| Hosts | Multi-host core kept; Claude-only parts (live evals, project settings, Playwright) form an optional layer that other hosts report as `not-verified` |
| Repository registry and playbooks | Still no registry. Repository facts live in a `## Agent playbook` section of each product repository's own `AGENTS.md`, from a template, written only on approval there |
| Task start | Adopted: read the playbook, fetch only the base, start new work from `origin/<base>`, rebase a continued branch only when clean and unpushed, never stash or force-push; side sessions save their work as a commit or patch |
| Graphs | Still on demand, plus a per-repository opt-in (`Graph: auto`) that refreshes the baseline at task start; refresh failures never block a task |
| Retros and learning | Adopted: a retro after each workflow in ignored `.tinker/retros/`, and a learn pass whose at most three edits are kept only when the live gate passes. This reverses the earlier "no automatic retrospectives" decision, keeping retros short and local |
| Evaluation | Added a live Claude Code runner and gate next to the offline grader; the user records the first baseline |
| Guardrails | Adopted the destructive-Git deny and ask rules as Claude project settings, complementing the installed hook gate |
| Live passes | Adopted as a Claude layer: the official Playwright plugin, isolated profile, localhost-only origins, evidence under `.tinker/evidence/` |
| Helpers | Added the Explorer, a search-only role whose `tier: light` gives it Claude's small model and a charter-only brief. A cost hint for one helper, not a model matrix |
| Routines and utilities | Weekly maintenance, monthly upgrade scan and per-repository graph refresh became ready templates; a test-log filter was ported to Python and now always keeps totals and states what it trimmed |
| Front door | A `tinker` skill offers `status`, `learn`, `eval`, `playbook`, `schedule` and `help`; natural language remains sufficient |
| Not adopted | Headless launcher, team registry and work-item routing, fixed evaluation model, bundled database server |

Two outside ideas were folded in as instructions, without their packages: a grill mode
in shaping (one decision at a time with a recommendation, inspired by Matt Pocock's
`grill-me` skill) and a minimalism ladder in implementation and review (does the code
need to exist, does the codebase or standard library cover it, inspired by the
`ponytail` ruleset). Neither package's hooks or files were installed, so nothing runs
beside Tinker's own hook runtime.

## 2026-09-26: renamed to Tinker

The project formerly named Tinker Bot is now Tinker, and its history was rewritten
into technical commits. Revisions cited below, such as `c7805fd`, belong to the
pre-rename history, which is kept under the local tag `archive/tinker-bot`.

| Former | Now |
| --- | --- |
| Plugin `tinker-bot@tinker-bot-local` | `tinker@tinker-local` |
| Skills `tinker-bot-<name>` | `tinker-<name>` |
| User state `~/.tinker-bot/`; checkout state `.tinker-bot/` | `~/.tinker/`; `.tinker/` |
| Runtime `scripts/tinker_bot.py` | `scripts/tinker_runtime.py`. The tamper guard matches the runtime's name anywhere in a command, and a bare `tinker` would match every path inside a Tinker checkout |

The name is shared with the original PowerShell Tinker analyzed below and with an
organization's edition, which can be installed under the same plugin id and home
folder. The installer therefore decides ownership only from its own records. It
refuses an app where a Tinker plugin it did not record is enabled, and it never reads
or rewrites an `apps.json` that it did not write. Installations made under the former
name are not migrated; uninstall them with the installer at `archive/tinker-bot` first.

## 2026-09-26: a dependable generic team

The refactor strengthened the existing design instead of replacing it. It was planned
after comparing this project at pre-rename revision `c7805fd` with an organization's
published edition of Tinker (baseline `750955d`, later `7866b0f`, which merged its
team-domains branch and a separate evaluation fix). Its application verification recipes, team
playbooks, shared retrospectives and evaluation-backed improvement informed this
change; its aggregate evaluation scores were not copied, and no improvement of equal
size is claimed. Its browser-planning evaluation showed planning behavior, not actual
browser verification.

| Area | Decision |
| --- | --- |
| Lead, specialist roles and native host execution | Preserved, with provider defaults |
| Application verification recipes | Adapted into optional, generic UI/API/CLI verification guidance |
| Team playbooks and shared retrospectives | Adapted as optional domain packs and evidence-backed learning |
| Evaluation-backed improvement | Adopted, keeping Tinker's evidence provenance and adding independent coverage checks |
| Repository registry, default product, work-tracker routing | Not imported into the generic core |
| Mandatory graph refresh, automatic retrospectives after every task | Not adopted |
| Fixed models, larger worker budgets, headless launcher | Not adopted |
| Maintenance routines | Opt-in native-scheduler prompt templates; nothing is scheduled automatically |

Defects fixed with regression tests first: approval identity that ignored edit contents
and scheduler arguments; a single-use grant that concurrent retries could all consume on
Windows (concurrent `os.replace` renames of one file all report success there);
unreadable session state and stale presence writes that could turn an unattended run
into an attended one; gated payloads missing required fields passing silently; installer
writes and a directory marker that could overwrite or delete files the installer did not
own; one app's update marking every app current; and Graphify branches chosen from two
product names.

Compatibility changes: earlier grants and pending approvals without a fingerprint are
expired; Graphify needs `--baseline-branch` to establish a baseline for every
repository, including those that relied on a built-in default; the installer keeps
`apps.json` after a full uninstall, as the ownership record of the runtime it leaves.

## Original specification review and reference analysis

Two independent read-only workers reviewed the specification and reference
repository before implementation: Systems Architect and Adversarial Reviewer.
Both recommended removing the runtime. Their source findings agreed; there was
no unresolved architectural disagreement. The architect favored optional native
reviewer adapters; the reliability reviewer stressed that those cannot guarantee
isolation under all parent settings. Keep small adapters, require effective
permission checks, and explicitly fall back when restrictions are unavailable.

The subsequent user-approved software-team plan expanded roles and native adapters,
replaced the lifetime worker ceiling with a concurrency limit, and made substantial
job handoffs portable across hosts. It preserved the instruction-first architecture.

| Original assumption | Review finding | Decision and resulting change |
| --- | --- | --- |
| Persistent teammates need a state engine | Role identity is not a process | Lead plus eight specialist charters, native sessions and shared handoffs |
| Every responsibility needs a skill | Questions, checks and learning need no separate workflow | Six focused skills, including on-demand clean-commit Graphify and team status; other responsibilities use role guidance |
| Existing CLI is a useful starting point | It records unexecuted success | No orchestration CLI or provider adapter code; focused Graphify and in-app hook helpers |
| Tool-policy JSON enforces safety | The reference only renders tool names | Native restrictions plus candid fallback; the optional PreToolUse hook is native enforcement, classified in code |
| Two-worker setting is a hard total quota | Sequential specialists need a concurrency rule | Two active helpers, one writer including Lead, no lifetime ceiling |
| Automatic memory makes agents persistent | Stale and irrelevant entries enter context | Selected scoped notes; deliberate candidate promotion; turn one lists only validated note paths |
| Cleanup and routines are core services | They add state and can remove user work | Direct workflow checks; no automatic cleanup; hooks only in the optional in-app runtime |
| Static policy tests demonstrate behavior | They only find words in instructions | Separate package checks, synthetic grader tests and observed runs |

## Reference component disposition

Reference analyzed: the original PowerShell Tinker, revision `733c0a9a96c5ec1395e38bfaee2105b780c758a5`.
REMOVE means excluded from this project, not deleted from the reference repository.

| Reference component | Disposition | Replacement |
| --- | --- | --- |
| AGENTS, CLAUDE, GEMINI | SIMPLIFY | Concise canonical agreement and relative imports |
| `config/bots/`, `tinker-bot.ps1` | REDESIGN | On-demand role charters and native workers |
| `config/skills/` | REMOVE | One physical source per workflow |
| `skills/` and references | KEEP / SIMPLIFY | Six focused workflows; common policy centralized |
| `config/routines.json`, `tinker-routine.ps1` | REPLACE WITH NATIVE CAPABILITY | Workflow steps; user-requested host scheduling, with a validated `schedule-plan` |
| `config/approvals.json`, `tinker-approval.ps1` | REPLACE WITH NATIVE CAPABILITY | Authorization boundaries, host permissions and the optional hook gate (no policy file) |
| `tinker.ps1`, root wrappers, `tinker-router.ps1` | REMOVE | Host reasoning, execution and configured models |
| `tinker-context.ps1` | REPLACE WITH NATIVE CAPABILITY | Search, focused reads and host compaction |
| `tinker-memory.ps1`, `tinker-learner.ps1` | REDESIGN | Optional knowledge notes and candidates |
| `tinker-workspace.ps1` | REPLACE WITH NATIVE CAPABILITY | Host sessions and Git worktrees |
| `tinker-graphify.ps1`, graph hooks | REPLACE | Small Python helper runs upstream Graphify on demand for a clean baseline and selected worktree; output stays in ignored `.tinker/graphs/`; other tools' graph state is never written |
| `tinker-cleanup.ps1`, report cleanup | REMOVE | Explicit scoped cleanup when needed |
| Repository registry and resolver | REMOVE | Explicit target paths; no default product |
| Installer and uninstaller | REDESIGN | Local checkout, or the opt-in user-level installer with ownership records |
| Diff and log helpers | REPLACE WITH NATIVE CAPABILITY | Git/test-runner filters, preserving failure summaries |
| Product-specific log decryption | REMOVE | Product-specific concern outside this package |
| Doctor, docs, benchmarks, evals and tests | REDESIGN | Operational documentation and honest validation |

Concrete reference evidence: `scripts/tinker.ps1:183-190` reports direct work
without execution; `:203-242` manufactures worker outcomes and token counts;
`:260-268` saves fabricated verification into handoff/memory. The router invents
provider availability at `scripts/tinker-router.ps1:33-37` and fixes model names
at `:39-55`. Worktree removal uses force at `scripts/tinker-workspace.ps1:340`.
Memory has a positive baseline for unrelated entries at
`scripts/tinker-memory.ps1:227-248`. The eval runner's live path ignores exit
status at `scripts/test-evals.ps1:142-153`; its static summary overclaims at `:165`.
The reference test suite mutates conventions at `tests/tinker.tests.ps1:950-962`,
so it was inspected rather than executed in place.

## 2026-09-24: the in-app runtime

A task whose scope included architecture reversed four earlier decisions for one
concrete need: teammates used from inside Claude Code, Codex and Antigravity, in any
product project, without a terminal. Turn-one context, enforcement on the tool loop
and presence cannot come from instructions.

| Earlier decision | Change | Why hooks, not instructions |
| --- | --- | --- |
| No hooks | Lifecycle hooks run by each host's own loop; still no daemon, launcher, database or scheduler | Context at session start, presence at turn boundaries |
| Approvals replaced by host permissions | PreToolUse gate on the safety list; never-grantable tamper list | A hook deny binds even in bypass modes |
| Scoped notes only | Turn one lists validated note paths and open checkpoint ids for the current repository | No bodies, free text or scoring enter context |
| No installer; start in this checkout | Opt-in user-level installer through each host's CLI; project mode remains | The team must load in any project |
