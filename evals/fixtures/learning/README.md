# Learning fixtures

Candidates for the `learning-review` and `learning-promotion` cases in
[the catalog](../../cases.json). Copy them, with `validated-note.md`, into the
disposable repository's knowledge folder before a run, then commit the repository.

| File | Expected outcome on promotion |
| --- | --- |
| `candidate-valid.md` | Promotable after re-running its check against current source |
| `candidate-stale.md` | Stays candidate or becomes stale: its cited file hash no longer matches |
| `candidate-unsupported.md` | Stays candidate: it has no verification evidence |
| `candidate-conflicting.md` | Stays candidate: it contradicts `validated-note.md` |

The expected outcomes are for the reviewer. Do not show this table to the agent under test.
