# Frontend design

Use for any task that designs, builds, restyles, polishes, animates, critiques or
reviews a user interface: web pages, product UI, components, motion, mobile web,
React Native and Swift screens. The user's request, the product's own design system
and its playbook come first. The skills below decide what those leave open and never
override repository conventions or [safety](safety.md). The
[design skills study](../docs/design-skills.md) holds the evidence, pins and upkeep.

Load a skill natively by name where the host lists it. Otherwise read its `SKILL.md`
from `~/.claude/skills/<name>/` or `~/.agents/skills/<name>/` (user level), or from
`.agents/skills/<name>/` (a project install). Give a helper without a skill tool that
path. Every UI edit loads `impeccable` and follows its setup: context first, then its
craft floor right before the edit. On first run its launcher fetches its own binary;
that is part of the user's install, not a task download. If the launcher is refused or
fails, use its documented fallback and read `PRODUCT.md` and `DESIGN.md` directly.
Add the specialist the task names. A skill missing on this machine is reported, not
improvised. Without `impeccable`, apply the gate, floor and finish below by hand and
say so. The user installs the skills by running
`python scripts/install_apps.py --skills` in the Tinker checkout.

| Task | Skill |
| --- | --- |
| Design, redesign, shape, critique, audit, polish or harden any UI (every UI edit) | `impeccable` |
| Component polish and the details that make it feel finished | `emil-design-eng` |
| Marketing, landing or company website with no design system | `design-taste-frontend` |
| Style, palette, font pair, chart or stack-guide candidates | `ui-ux-pro-max` |
| Build an animation or transition; several parts moving together | `animate`; `choreograph` |
| Drag, swipe, sheet or another gesture that tracks the finger | `gestures` |
| Review motion in a diff | `review-animations` |
| Audit a codebase's motion; find missing motion (plans only) | `improve-animations`; `find-animation-opportunities` |
| Remove motion an interface does not need | `remove-animations` |
| Janky or dropped-frame motion | `animation-performance` |
| Springs, materials, Apple-style feel | `apple-design` |
| Web app on phones, PWA, touch | `mobile-native` |
| React Native or Expo motion; Swift code | `animate-expo`; `write-swift` |
| Stress-test a screen with worst-case data | `break-ui` |
| Choose a UI library; Sonner toasts | `pick-ui-library`; `ask-sonner` |
| Several throwaway versions to compare | `prototype` |
| Name a motion effect | `animation-vocabulary` |

## Before the first UI edit

1. Read the product's `DESIGN.md`, `PRODUCT.md`, tokens and components, and the screens
   next to the change. They outrank any skill default. A copy fix or a one-property
   change matches them and skips steps 3 and 4.
2. Name the surface's mode, using Impeccable's terms: Persuade, Operate, Read or
   Experience. On Operate and Read surfaces, craft shows as precision and restraint.
3. If there is a UI but no `DESIGN.md` and the change makes visual decisions (a new
   screen, component or layout, or a style change), capture what exists first, with
   `impeccable` `document`. That format is the canonical `DESIGN.md`. Write it to the
   product only where the task or playbook allows a new file. Otherwise keep it in the
   task notes. Captures from other tools, such as the design-md-chrome extension the
   user can run on a live site, are reference input. Never save them as `DESIGN.md`.
4. With nothing to capture, write a direction before any CSS and put it in the plan or
   brief. Cover:
   - the audience and the job the screen does;
   - two or three named references and one anti-reference;
   - the layout posture;
   - the type pair;
   - the palette, with one accent;
   - the motion stance.

   `ui-ux-pro-max` may supply candidates. They are never the decision, and nothing it
   produces is persisted unverified.
5. Refinement keeps the identity. Change only what the task names; a version the user
   prefers is the reference. Redesign only when the user asks for one.

## Precedence

1. The user's request, then the product's `DESIGN.md`, tokens and playbook. The
   floor's look items yield to them; its other items do not.
2. `impeccable`.
3. The specialist for its area. Emil Kowalski's skills cover motion and polish.
   `design-taste-frontend` covers a site with no design system, and its own palette and
   `:root` never replace a product's tokens.
4. `ui-ux-pro-max` data.

## Anti-generic floor

Every UI change meets this floor, whichever skill ran. The first three items are look
items. They govern new choices and yield to a product's `DESIGN.md` and tokens, so an
established violet accent or system display face stays. The rest hold everywhere. The
floor restates rules from Taste, open-design and ui-ux-pro-max; the sources are in the
study.

- No look by habit:
  - no indigo or violet accent and no two-stop hero gradient;
  - no glassmorphism, glow or parallax as decoration;
  - no emoji as icons;
  - no colored left-border cards and no cards inside cards.
- Colors come from tokens, with raw hex only in the token layer. Use one accent,
  sparingly.
- At most two typefaces, and never a bare system font for display. Body lines run
  50–75 characters. Use tabular figures where numbers align.
- One primary action per screen or region; a hero has at most two.
- Real content:
  - no invented metrics, reviews, logos or testimonials (use labelled placeholders);
  - headings name things, and buttons are a verb and an object;
  - no filler words such as "elevate", "seamless" or "unlock".
- Motion only for space, time or state:
  - under 200 ms for frequent actions and under 500 ms otherwise;
  - none on keyboard actions;
  - no scroll-jacking and no fade-in on every block;
  - reduced motion hides nothing.
- Every interactive part has default, hover, focus-visible, active, disabled, loading,
  empty and error states where they apply.
- Contrast is at least 4.5:1 for text and 3:1 for large text and controls, with dark mode
  checked on its own. Touch targets are at least 44 px, and focus is never hidden.
- Pages work at 375 px (320 px for public sites), at 1440 px and in landscape, without
  horizontal scroll.
- Never use a real brand's look as a product's style.
- Screenshot test: someone outside the team could name the product from a screenshot.

## Finish

- Take screenshots at phone and desktop widths, plus the states the change touches, per
  [application verification](app-verification.md).
- Name each skill used next to its evidence. A checker's or detector's output counts only
  when it actually ran. This covers Impeccable's audit or critique and Taste's checker or
  gate.
- When the user corrects the design, suggest they run `learn-taste`, so the correction
  becomes a rule in `DESIGN.md`.
- Tool output that is not part of the change stays out of the product's commit. That
  includes `.taste-skill/`, `shots/`, `share.jpg` and preview files. Screenshots kept as
  evidence go where [application verification](app-verification.md) puts evidence.

## Ownership and safety

- Changing code with any skill needs writing ownership.
- Helpers without writing ownership, such as Designer and Reviewer, may read any routed
  skill as guidance and return findings. They never run a skill's scripts: Impeccable's
  launcher, `search.py` and Taste's scripts all stay with the writer.
- Only the Lead, while it holds writing ownership, loads `design-taste-frontend`; a
  helper never does, because its Stop hook would hold the parent session. Once a build
  is armed, the hook holds each turn until the finish gate passes or its rounds run out
  (3 by default).
- A skill's own steps run only inside the task's authorization. These include init files,
  `DESIGN.md`, design hooks, browser checkers, package installs, and icon or photo
  downloads. Add no new dependency, file outside the task or download unless the
  playbook allows it or the user asks.
- `design-taste-frontend` scripts start the local Chrome on 127.0.0.1 and fetch icons
  and photos from public CDNs. Never pass `icons.mjs` a real `--profile` folder: it
  deletes it.
- For `ui-ux-pro-max`, run `python <its folder>/scripts/search.py`. The
  `${CLAUDE_PLUGIN_ROOT}` path in its text exists only inside its own plugin. Its
  `--persist` and `--preview` options write files; use them only when the task asks for
  those files. Never use its sibling skills (paid image APIs, keys) or `uipro update`
  (an unpinned global install).
- In an EU product, self-host the Google Fonts that a skill's pages or previews load.
