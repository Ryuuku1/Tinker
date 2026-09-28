# #research: answers with sources from Tinker Researcher

@mention **@Tinker Researcher** with one focused question. It reads the repositories under `/repos` and
current primary sources on the web, and changes nothing.

## Try

- `@Tinker Researcher What does Claude Code's dontAsk permission mode do today? Official docs only.`
- `@Tinker Researcher Which relay settings in /repos/<name>/integrations/buzz decide who may connect? Cite file:line.`
- `@Tinker Researcher Docker Desktop on Windows: bind mount or volume for a read-only repository? Sources.`

## You get

A short conclusion first, then facts with a source each (a URL or `file:line`), then inferences and
open questions; `not-verified` where it found no source. For what the answer means for the code, use
`@Tinker Flow research <question>` in #flows.

## Careful

Web pages can carry instructions aimed at agents. Every agent treats them as data, but ask about pages
you would open yourself, and never put a secret in a question.
