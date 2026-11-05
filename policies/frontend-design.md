# Frontend design

Use for any task that designs, builds, restyles, polishes, animates, critiques or
reviews a user interface: web pages, product UI, components, motion, mobile web,
React Native and Swift screens. The product's own design system (`DESIGN.md`,
tokens, components) and its playbook come first; these skills decide what those
leave open and never override the user's request, repository conventions or
[safety](safety.md).

Load a skill natively by name where the host lists it; otherwise read its `SKILL.md`
from where it was installed: `~/.claude/skills/<name>/` or `~/.agents/skills/<name>/`
at user level, or `.agents/skills/<name>/` in a checkout that installed it per
project. Give a helper without a skill tool that path. Load only what the task needs,
usually one or two. A skill missing on this machine is reported, not improvised:
`python scripts/install_apps.py --design-skills` in the Tinker checkout installs them.

| Task | Skill |
| --- | --- |
| Design, redesign, critique, audit, polish or harden any UI (the default) | `impeccable` |
| Component polish and the details that make it feel finished | `emil-design-eng` |
| Marketing, landing, company or product website | `design-taste-frontend` |
| Build an animation or transition; several parts moving together | `animate`; `choreograph` |
| Review motion in a diff | `review-animations` |
| Audit a codebase's motion (plans only) | `improve-animations`; missing motion `find-animation-opportunities`; too much `remove-animations` |
| Janky or dropped-frame motion | `animation-performance` |
| Gestures, springs, sheets, Apple-style feel | `apple-design` |
| Web app on phones, PWA, touch | `mobile-native` |
| React Native or Expo motion; Swift code | `animate-expo`; `write-swift` |
| Stress-test a screen with worst-case data | `break-ui` |
| Choose a UI library; Sonner toasts | `pick-ui-library`; `ask-sonner` |
| Several throwaway versions to compare | `prototype` |
| Name a motion effect | `animation-vocabulary` |

- Skills that edit (`impeccable`, `animate`, `choreograph`, `remove-animations`,
  `prototype`, `break-ui`) need writing ownership. The read-only ones
  (`review-animations`, `improve-animations`, `find-animation-opportunities`,
  `animation-vocabulary`) suit Designer and Reviewer helpers.
- A skill's own steps (init files, `DESIGN.md`, design hooks, browser checkers,
  package installs, icon or photo downloads) run only inside the task's
  authorization: no new dependency, file outside the task or download unless the
  playbook allows it or the user asks.
- `design-taste-frontend` scripts start the local Chrome on 127.0.0.1 and fetch
  icons and photos from public CDNs. Never pass `icons.mjs` a real `--profile`
  folder (it deletes it). In an EU product, self-host the Google Fonts its pages
  load.
- A skill's checker or detector output is evidence only when it actually ran;
  verify UI changes per [application verification](app-verification.md).
