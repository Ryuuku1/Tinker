# Design skills: study and maintenance

Study of 2026-11-19. Question: how should Tinker use five design repositories so its UI
work stops looking generic, and how does that keep working after upstream changes?
The rules themselves live in [frontend design](../policies/frontend-design.md). This
document holds the evidence, the decisions and the maintenance procedure.

## Decisions at a glance

| Repository | Verdict | How Tinker uses it |
| --- | --- | --- |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Install one skill, pinned | `ui-ux-pro-max` proposes style, palette, type and chart candidates. It is a lookup, never a decision |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Keep, pinned to v2.5.1 | `design-taste-frontend` for marketing and company sites that have no design system |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | Do not install | Its craft rules are restated, with attribution, in the policy's anti-generic floor |
| [bergside/design-md-chrome](https://github.com/bergside/design-md-chrome) | User-side tool, optional | The user can capture a live site's styles as reference input. The agent cannot install it |
| [webfuse-com/awesome-claude](https://github.com/webfuse-com/awesome-claude) | Skip | A link list with no design rules and nothing to install |

The skills already installed stay: Impeccable is the default for every UI edit, and
Emil Kowalski's skills cover motion and polish. Every skill repository is now pinned to
a full commit, and Impeccable stays on its pinned npm CLI.

## What changes on the user's machine

Re-running `python scripts/install_apps.py --design-skills` after this change:

- updates Emil Kowalski's 17 skills to commit `64eb3de` and adds `gestures`, `ask-emil`
  and `learn-taste`. The last two run only when the user types them;
- moves Taste to v2.5.1. **v2.5.1 adds a Stop hook to the skill**
  (`node gate.mjs --hook claude`, timeout 600 s). Claude Code adds it once the skill is
  invoked. It blocks the end of a turn only when a build is armed (by `gate.mjs --start`
  or the skill's `start.mjs deal`). It holds the turn until the finish gate passes or
  its rounds run out (3 by default). This is the one place where the
  installer's "no hooks" stance changes: the hook is the skill's own, scoped to it, and
  it is what makes Taste's checks binding. Fallback: pin
  `822e0b9d872e10deb931afad2c6c2bd943cf4c7b` (v2.5.0), which has no hook. Its content
  hash equals the `design-taste-frontend` entry in the lock reviewed on 2026-11-04;
- adds `ui-ux-pro-max` (Python standard library only, no network);
- leaves Impeccable on CLI 4.8.0 with its hook off.

## Why the output came out generic

These are inferences from Tinker's rules as they stood, not measurements.

1. **Routing was advisory.** "Load only what the task needs, usually one or two" let an
   agent skip every skill on a small UI change, and the minimal-diff ladder then fills
   the gaps with framework defaults.
2. **No direction before code.** Nothing required naming the audience, references, type
   and palette before the first CSS edit, so agents reached for the most common pattern
   in their training.
3. **No design system meant invented defaults.** With no `DESIGN.md`, each task picked
   its own colors and spacing.
4. **Verification had no design gate.** Tests and screenshots proved the UI worked, not
   that it was specific. A checker's output counted only if it ran, and nothing asked
   for it.
5. **Unpinned skills drifted.** Taste's installed copy was an untagged commit between
   v2.5.0 and v2.5.1, and all 17 of Emil's skills changed after the lock was reviewed.
   What agents loaded was not what had been reviewed.
6. **Helpers could not run the skills.** Read-only Designer helpers cannot run Impeccable
   or Taste scripts, so delegated design work fell back to prose.

The opposite failure matters too. Mumu's owner rejected a full redesign and asked for
"calm, same theme". The rules must therefore keep an existing identity when refining.
Being "less generic" must never mean restyling what already works.

## The five repositories

Every clone was shallow and treated as untrusted data. Nothing from it was run, except
ui-ux-pro-max's `search.py` (standard library only) from an empty folder.

### ui-ux-pro-max-skill

MIT, `skill.json` 2.15.0. Tag v2.15.0 is `a38d04c` (2026-08-14). Reviewed and pinned at
`2de1134` (2026-11-19), which changes 34 files of the skill since the tag.

- **What it is:** seven skills under `.claude/skills/`. The core `ui-ux-pro-max` is a CSV
  knowledge base with a BM25 search script: product types, styles, palettes, font pairs,
  UX rules, charts and 22 stack guides (including WPF, WinUI and Avalonia).
- **What is useful:** its priority order (accessibility > touch > performance > style …
  charts), its pre-delivery checks (375 px and landscape, dark-mode contrast checked
  separately, 44 pt targets, focus never covered, one primary action per screen, tabular
  figures), its stack guides and chart choice, and "do not persist unverified output".
- **Evidence that its output is a candidate:** `search.py "childcare nursery parent
  communication app" --design-system` returned Claymorphism, pink `#F472B6` and
  Fredoka/Nunito, which are category defaults. Taken as a decision, that is exactly the
  generic result this change is meant to stop.
- **Conflicts with Tinker's direction:** it calls `--design-system` required and its
  `MASTER.md` the source of truth, it recommends glassmorphism and parallax, and "always
  transition 150–300 ms" contradicts Emil (no animation on keyboard actions).
- **Breakage to work around:** its `SKILL.md` calls
  `python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py"`, which
  exists only inside its own plugin. Agents run `python <skill folder>/scripts/search.py`.
- **Excluded:** the six other skills (`design`, `brand`, `slides`, `design-system`,
  `ui-styling`, `banner-design`) need paid image APIs, keys or shadcn installs. Also
  excluded are `uipro update` (an unpinned global `npm install`) and the stale
  `uipro-cli` npm package (2.2.3).
- **Writes:** nothing, unless `--persist` (writes `design-system/`) or `--preview` (an HTML
  file that loads Google Fonts) is passed.

### taste-skill

MIT. v2.5.0 is `822e0b9` (2026-11-05) and v2.5.1 is `f6b7657` (2026-11-07). There were 8
releases between 2026-10-13 and 2026-11-07, so a fast cadence.

- **What it is:** one skill, `design-taste-frontend`, for websites only. It deals a palette
  and type by trade, writes the page and runs a checker in a real local Chrome.
  v2.5.1 adds the finish gate (`gate.mjs`), copy lint, a copy layer, a 320 px phone check,
  a hero entrance with one or two moments per page, and licensed stand-in photographs.
- **What is useful:** the strictest anti-slop rules of the five. No fade-in on every
  block, no parallax text, no scroll-jacking. No invented reviews, figures, stock photos
  or fake logos, and no captions under images. Headings name things, buttons are verb
  plus object, a hero has at most two actions, and reduced motion hides nothing. It
  bans slop words ("elevate", "seamless"…). The checker enforces this in a browser.
- **Conflicts:** it ignores `DESIGN.md` and design systems, keeps its own `:root`, and
  treats `kit-edited` as not waivable. Applied to a product with an identity, it
  replaces that identity, which Impeccable's "refinement preserves" forbids. So Taste is
  routed only to marketing and company sites with no design system, and product tokens
  win.
- **Hazards:** `icons.mjs --profile <dir>` deletes that folder (`rmSync`, `icons.mjs:520`)
  when it is absolute or inside the project. Only `.taste-skill/chrome-*` or the OS temp
  folder is safe. Network use: Google Fonts, jsDelivr, picsum, Wikimedia. Writes
  `.taste-skill/`, `assets/`, `shots/` and `share.jpg`. The Stop hook waits on the parent
  session when a subagent loads the skill, so only the Lead loads it, while holding
  writing ownership, and never a helper.

### open-design

Apache-2.0, v0.27.2, roughly weekly 0.x releases. Reviewed at `0725880`
(`07258801b9e4ae80553816bb1606af7aa9a63dff`, 2026-11-18).

- **What it is:** a Next.js and Electron app with a Node 24 daemon on 127.0.0.1:7456, an
  MCP server, an `od` CLI that is not on npm, and 169 skills, of which 85 are stubs
  pointing upstream. It includes copies of Emil's, Taste's and Impeccable's skills
  under colliding names. The clone is 531 MB.
- **Why not install:** the daemon runs Claude with `--permission-mode bypassPermissions`
  (`apps/daemon/src/runtimes/defs/claude.ts:116`) and Antigravity with
  `--dangerously-skip-permissions`. Its MCP server, described as read-only, exposes write
  and delete tools. Analytics are on by default, and PostHog safety telemetry cannot be
  turned off. `.claude/skills/od-contribute` runs `git push` and opens pull requests.
  Its brand design systems (Airbnb, Apple, BMW…) copy real trade dress.
- **What Tinker takes:** the craft rules under `craft/` (anti-AI-slop, color, type,
  hierarchy, states, motion, critique), restated in Tinker's own words in the policy's
  floor:
  - no default indigo or violet accent, no two-stop hero gradient, no emoji icons, no
    colored left-border cards;
  - no invented metrics (use labelled placeholders);
  - raw hex only in the token layer, and one accent used about twice per screen;
  - contrast 4.5:1 and 3:1;
  - at most two typefaces, never a bare system font as display, 50–75 characters per
    line;
  - one dominant element per region, and every state;
  - motion only for space, time or state (under 500 ms, under 200 ms for frequent
    actions);
  - a direction with named references settled before CSS;
  - a five-dimension self-critique with evidence;
  - the screenshot test: someone outside the team can name the product from a screenshot.
- **Considered and skipped:** Vercel's `web-design-guidelines`. The original fetches its
  rules from `main` at run time. open-design's copy is pinned, but installing it means
  pulling the whole 531 MB repository, and Impeccable's audit plus the floor cover it.

### design-md-chrome

MIT, v0.4.0, last commit `8e07614` (2026-05-25), slow cadence.

- **What it is:** a Chrome MV3 extension (activeTab, scripting, storage, downloads). It
  samples about 280 elements of the open page and writes a TypeUI `DESIGN.md` or
  `SKILL.md`, covering typography, colors, spacing, radius, shadows, motion, accessibility
  (WCAG 2.2 AA), tone, rules, and quality gates over seven required states (default,
  hover, focus-visible, active, disabled, loading, error). It makes no network calls.
- **How Tinker uses it:** the user loads it unpacked in their own Chrome; an agent cannot
  install it. It helps when a product has a live site but no `DESIGN.md` and no code
  access. Its output is reference input. Impeccable's `document`, run on the code, writes
  the product's canonical `DESIGN.md`.

### awesome-claude

CC0, last commit `a1cce8e` (2026-09-30): a curated list of Claude resources and a VS Code
theme. It has no design rules and nothing to install, so it can only be a place to look
for new sources by hand.

### Already installed: Impeccable and Emil Kowalski

- **Impeccable** (CLI 4.8.0, 2026-10-26; npm is at 4.10.0 on 2026-11-18, a release every
  2–5 days). Before any UI edit it loads `PRODUCT.md`, `DESIGN.md` and a surface brief
  through `scripts/impeccable context`, then reads its craft floor. It names the
  surface's mode (Persuade, Operate, Read, Experience) and follows "refinement preserves;
  redesign replaces". This is the right default, so the policy makes it mandatory rather
  than optional. Its launcher downloads a binary on first run. The policy treats that
  download as part of the user's install, and uses the skill's own fallback (read
  `PRODUCT.md` and `DESIGN.md` directly) when the launcher is refused.
- **Emil Kowalski** (`emilkowalski/skill`, no tags). Markdown only, with no scripts, hooks
  or `allowed-tools`. The commits since the 2026-11-04 lock fix wrong APIs and
  cross-skill contradictions (`0f2e23b`) and add `choreograph` changes, `gestures`,
  `learn-taste` and `ask-emil`. `learn-taste` turns a session's design corrections into
  rules in `DESIGN.md`, which is the loop that keeps a product from drifting back to
  generic.

## How Tinker uses them

The [policy](../policies/frontend-design.md) carries the rules. In short:

1. **Gate before the first UI edit.** Read the product's `DESIGN.md`, `PRODUCT.md`,
   tokens and components. When `DESIGN.md` is missing and the change makes visual
   decisions (a new screen, component or layout, or a style change), capture what exists
   first. A copy fix or a one-property change only matches the screens around it. A
   product with nothing gets a written direction before any CSS: mode, audience, named
   references and one anti-reference, layout posture, type, palette and motion stance.
2. **One `DESIGN.md` format.** Impeccable's (YAML token front matter, its sections and
   the `.impeccable/design.json` sidecar) is canonical. TypeUI and open-design captures
   are reference input, never written as the product's `DESIGN.md`, because the three
   formats are incompatible.
3. **Precedence.** The user and the product's own system come first, then Impeccable,
   then the specialist skill for its area (Emil for motion and polish, Taste for sites
   with no system), then ui-ux-pro-max data.
4. **A floor every UI change meets,** whichever skill ran. Its look items (accent,
   gradients, type) yield to a product's own `DESIGN.md`. Its accessibility, content,
   state and motion items do not.
5. **Finish with evidence.** Screenshots at phone and desktop widths, the skill used named
   next to its evidence, and a checker's output counted only when it actually ran.

## Pins

Pins live in two places that must agree: `DESIGN_SOURCES` in `scripts/install_apps.py`
(what is installed) and `skills-lock.json` (what was reviewed: `ref` and a content hash
per skill). A test fails when they disagree or a source is not pinned to a full commit.

| Source | Ref | Upstream label | Skills | Reviewed |
| --- | --- | --- | --- | --- |
| `emilkowalski/skill` | `64eb3deb9a5fbfa041faf783e0bc3fd635872e9c` | HEAD of 2026-11-15 (no tags) | all 20 | 2026-11-19 |
| `Leonxlnx/taste-skill` | `f6b76575f949707b4e3c37cd86cb44b0b98643e8` | v2.5.1 | `design-taste-frontend` | 2026-11-19 |
| `nextlevelbuilder/ui-ux-pro-max-skill` | `2de1134dc4d1cfe112934611ae5803ae17a1bd7e` | after v2.15.0 | `ui-ux-pro-max` only | 2026-11-19 |
| Impeccable CLI (npm) | `impeccable@4.8.0` | 4.8.0 | `impeccable` | 2026-11-04 |
| skills CLI (npm) | `skills@1.7.6` | 1.7.6 (npm latest 1.9.0) | installer | 2026-11-19 |

Tags can move, so pins are full commits and the table records the tag only as a label.
skills CLI 1.7.6 accepts `owner/repo#<ref>`. It clones a branch or tag with `--depth 1`
and fetches a bare commit separately. It writes the `ref` into the lock. This was verified
on 2026-11-19 by running the three pinned commands at project scope in an empty folder:
all 22 skills installed, and all 22 hashes matched an independent recomputation. The lock
that run wrote, the recomputed hashes and the script are kept on the reviewing machine in
`.tinker/evidence/design-skills-pins-20261119/` (not tracked).

## Maintenance

### Monthly check

The [monthly upgrade scan](../templates/routines.md#monthly-upgrade-scan) also compares
each `ref` in `skills-lock.json` and the two design CLIs pinned in the installer
(`SKILLS_CLI`, `IMPECCABLE_CLI`) with upstream. That means new commits for a source
without tags, such as Emil Kowalski's, and new tags or npm releases otherwise. It reports
in `.tinker/reports/upgrade-<date>.md` and changes nothing. A scan scheduled before
2026-11-19 keeps its old prompt, so update it from the template (or re-create it with
`/tinker schedule defaults`) before it covers the pins.
A newer upstream is not a reason to bump. Bump when a release fixes something Tinker
hits, or adds something the policy would route to.

### Bumping a skill pin

1. Read the upstream diff between the pinned ref and the candidate. Look for new scripts,
   hooks (`hooks:` in a `SKILL.md`), `allowed-tools`, network calls, file writes, deletes
   and changed skill names.
2. In an empty scratch folder, with `DO_NOT_TRACK=1` and `DISABLE_TELEMETRY=1`, run the
   pinned CLI at project scope:
   `npx --yes skills@1.7.6 add <owner/repo>#<full commit> --skill <name or *> --yes --agent claude-code`.
   It writes `skills-lock.json` there.
3. Copy that source's entries into the repository's `skills-lock.json`, and change the
   commit in `DESIGN_SOURCES`. Never edit a hash by hand.
4. If a skill was renamed, added or dropped, update the routing table in the policy. Its
   names must exist in the lock, and skills that only the user can invoke
   (`disable-model-invocation: true`) stay out of it.
5. Run `python -B -m unittest discover -s tests`, add a line to the
   [design history](history.md), and commit.
6. The user re-runs `python scripts/install_apps.py --design-skills` and starts a new
   chat. Only the user runs the installer.

### Bumping a CLI

- **skills:** read the release notes for changes to `#ref` parsing, the lock format or
  the hash. Repeat step 2 above with the new version and compare hashes with the lock.
  Then change `SKILLS_CLI`.
- **impeccable:** read the changelog. Install it in a scratch folder with
  `npx --yes impeccable@<version> install --no-hooks --yes --providers=claude` and diff
  the installed skill. Then change `IMPECCABLE_CLI`. The launcher's first-run binary
  download makes this the one pin whose content the lock does not hash.

### Rolling back

A rollback is a bump to the previous commit. Follow steps 2 to 6 with it, so the lock
entries get their `ref` from a real install. Entries restored from before 2026-11-19
have no `ref`, and the test rejects them. For Taste,
`822e0b9d872e10deb931afad2c6c2bd943cf4c7b` (v2.5.0) removes the Stop hook.

### Signs that something broke

- the installer fails on a source: the ref is gone or the repository moved;
- a skill named in the policy is missing in a new chat: renamed upstream, or the
  installer was not re-run;
- a turn will not end after Taste ran: its finish gate is armed and failing. Fix what
  it lists. The gate allows a set number of rounds (3 by default) and ignores a build
  idle for 24 hours, so it always lets the turn end eventually. Its rules are in the
  skill's `references/gate.md`;
- `search.py` not found: someone followed the `${CLAUDE_PLUGIN_ROOT}` path in the
  upstream text.

## Risks and guardrails

| Risk | Guardrail |
| --- | --- |
| Upstream changes content silently | Full-commit pins, lock hashes, a test that pins and lock agree, the monthly report |
| A skill replaces a product's identity | Precedence puts the product first; Taste only for sites with no system; refinement preserves |
| ui-ux-pro-max output taken as a design | It is a candidate list; its picks pass the floor and the direction, never persist on their own |
| Taste's Stop hook holds a session | Only the Lead with writing ownership loads it; its gate ends after its rounds; the fallback pin removes it |
| Impeccable's launcher downloads a binary | Part of the user's install of a pinned CLI; the skill's fallback reads the context files directly |
| Taste's `icons.mjs --profile` deletes a folder | The policy forbids a real `--profile` folder |
| CDN fonts in EU products | Self-host fonts that skills load from Google Fonts |
| Brand imitation | No real brand's look as a product style, so open-design's brand systems are excluded |
| Telemetry | `DO_NOT_TRACK`, `DISABLE_TELEMETRY`, `IMPECCABLE_NO_TELEMETRY` on every install; open-design not installed |

## What the tests prove

The unit tests prove the wiring:

- every source is pinned to a full commit;
- the pins and the lock agree;
- the routing table names only skills that are locked;
- the installer issues the pinned commands.

They do not prove that designs stop being generic. That needs a live design case judged
on screenshots against the floor, which is still open.

## Open items

- A live eval case for a UI change, graded on the gate and the floor.
- Impeccable 4.8.0 → 4.10.0 review.
- The same change in the organization's edition, which shares these skills.

## Sources

Each repository at the commit above; licenses MIT (ui-ux-pro-max, taste, design-md-chrome,
Emil Kowalski), Apache-2.0 (open-design) and CC0 (awesome-claude). The floor restates
rules in Tinker's own words with attribution; no upstream text is copied into Tinker.
