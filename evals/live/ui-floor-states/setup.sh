#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo board
cat > product/board/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Board</title>
  <link rel="stylesheet" href="tokens.css">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main>
    <h1>Tasks</h1>
    <ul id="tasks" class="tasks"></ul>
  </main>
  <script type="module" src="app.js"></script>
</body>
</html>
HTML
cat > product/board/tokens.css <<'CSS'
/* The only place raw colors live. */
:root {
  --color-text: #1f2328;
  --color-muted: #59636e;
  --color-surface: #ffffff;
  --color-border: #d1d9e0;
  --color-danger: #b42318;
  --color-focus: #0b5cad;
  --space-1: 4px;
  --space-2: 8px;
  --radius: 6px;
}
CSS
cat > product/board/styles.css <<'CSS'
body { margin: 0; font: 16px/1.5 Georgia, serif; color: var(--color-text); background: var(--color-surface); }
main { max-width: 40rem; margin: 0 auto; padding: var(--space-2); }
.tasks { list-style: none; margin: 0; padding: 0; }
.task { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2);
        padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border); }
.task button { min-height: 44px; padding: 0 var(--space-2); border: 1px solid var(--color-border);
               border-radius: var(--radius); background: var(--color-surface); color: var(--color-text); }
CSS
cat > product/board/app.js <<'JS'
// Renders the task list from the API.
const list = document.querySelector("#tasks");

export function renderTask(task) {
  const item = document.createElement("li");
  item.className = "task";
  item.dataset.id = task.id;
  const title = document.createElement("span");
  title.textContent = task.title;
  item.append(title);
  return item;
}

export async function load() {
  const tasks = await (await fetch("/api/tasks")).json();
  for (const task of tasks) list.append(renderTask(task));
}

load();
JS
commit_fixture board
