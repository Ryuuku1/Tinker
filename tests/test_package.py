"""Structural checks only: these do not establish live model compliance."""
import fnmatch
import importlib
import json
from pathlib import Path
import re
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".tinker", "__pycache__"}


def third_party(path):
    """Design skills and agents installed as-is by `npx skills` / `npx impeccable` (and their host copies);
    Tinker's own are named tinker*."""
    parts = path.relative_to(ROOT).parts
    return len(parts) > 2 and not parts[2].startswith("tinker") and (
        (parts[0] in (".agents", ".claude", ".gemini") and parts[1] == "skills") or parts[:2] == (".claude", "agents"))


def package_files():
    worktrees = ROOT / ".claude" / "worktrees"  # ignored linked worktrees hold whole other copies of the package
    return [p for p in ROOT.rglob("*") if p.is_file() and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
            and not p.is_relative_to(worktrees) and not third_party(p)]


def own_skills():
    return list((ROOT / ".agents/skills").glob("tinker*/SKILL.md"))


class PackageTests(unittest.TestCase):
    def test_canonical_native_imports(self):
        self.assertEqual((ROOT / "CLAUDE.md").read_text().strip(), "@AGENTS.md")
        self.assertEqual((ROOT / "GEMINI.md").read_text().strip(), "@./AGENTS.md")
        self.assertTrue((ROOT / "AGENTS.md").is_file())

    def test_local_markdown_links_resolve_inside_package(self):
        for path in package_files():
            if path.suffix != ".md":
                continue
            for target in re.findall(r"\]\(([^\s)]+)\)", path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#")):
                    continue
                with self.subTest(file=path.relative_to(ROOT), target=target):
                    dest = (path.parent / target.split("#")[0]).resolve()
                    self.assertTrue(dest.is_relative_to(ROOT))
                    self.assertTrue(dest.exists())

    def test_seven_unique_discoverable_skills(self):
        skills = own_skills()
        self.assertEqual(len(skills), 7)
        self.assertEqual(len([p for p in package_files() if p.name == "SKILL.md"]), 7)
        names = set()
        for path in skills:
            text = path.read_text(encoding="utf-8")
            match = re.match(r"\A---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n", text)
            self.assertIsNotNone(match, path)
            name, description = match.groups()
            self.assertEqual(name, path.parent.name)
            self.assertLessEqual(len(name), 64)
            self.assertLessEqual(len(description), 1024)
            self.assertNotIn(name, names)
            names.add(name)

    def test_claude_manifest_points_to_canonical_skills(self):
        manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest["skills"], ["./.agents/skills/"])
        self.assertNotIn("mcpServers", manifest)
        for target in manifest["skills"]:
            self.assertTrue((ROOT / target).is_dir())

    def test_codex_reviewer_requests_read_only_and_no_children(self):
        agent = tomllib.loads((ROOT / ".codex/agents/tinker-reviewer.toml").read_text())
        self.assertEqual(agent["sandbox_mode"], "read-only")
        self.assertEqual(agent["agents"], {"enabled": False})
        self.assertNotIn("model", agent)
        self.assertEqual(agent["features"], {"shell_tool": False})
        self.assertTrue(agent["developer_instructions"].strip())

    def test_project_sets_no_helper_cap_and_routes_ui_work_to_installed_skills(self):
        self.assertFalse((ROOT / ".codex/config.toml").exists())  # the Lead sizes the team; Codex's default caps
        self.assertNotRegex((ROOT / "AGENTS.md").read_text(encoding="utf-8"), r"(?i)maximum \*\*\d+ active helpers")
        self.assertIn("(policies/frontend-design.md)", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        table = (ROOT / "policies/frontend-design.md").read_text(encoding="utf-8").split("| --- | --- |")[1]
        names = set(re.findall(r"`([a-z0-9-]+)`", table.split("\n\n")[0]))
        self.assertGreaterEqual(len(names), 15)
        # installed per machine, so check the pinned list; `npx impeccable` keeps no lock entry
        pinned = set(json.loads((ROOT / "skills-lock.json").read_text(encoding="utf-8"))["skills"]) | {"impeccable"}
        self.assertEqual(names - pinned, set())

    def test_code_workflows_route_engineering_skills_with_fallbacks(self):
        for path in (".agents/skills/tinker-implement/SKILL.md", ".agents/skills/tinker-investigate/SKILL.md",
                     ".agents/skills/tinker-review/SKILL.md", "roles/engineer.md"):
            self.assertIn("policies/engineering-skills.md)", (ROOT / path).read_text(encoding="utf-8"), path)
        policy = (ROOT / "policies/engineering-skills.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| [^|]+ \| `([a-z:-]+)` \| ([^|]*) \|$", policy, re.M)
        self.assertGreaterEqual(len(rows), 8)
        study = (ROOT / "docs/engineering-skills.md").read_text(encoding="utf-8")
        for skill, fallback in rows:
            self.assertTrue(fallback.strip(), skill)  # a host without the skill still applies the rule
            self.assertIn(skill.split(":")[0], study)  # every routed source has a reviewed pin

    def test_claude_reviewer_has_only_file_read_tools(self):
        text = (ROOT / ".claude/agents/tinker-reviewer.md").read_text()
        tools = re.search(r"^tools: (.+)$", text, re.M).group(1).split(", ")
        self.assertEqual(set(tools), {"Read", "Grep", "Glob"})

    def test_gemini_reviewer_has_only_file_read_tools(self):
        text = (ROOT / ".gemini/agents/tinker-reviewer.md").read_text()
        tools = re.findall(r"^  - (\w+)$", text, re.M)
        self.assertEqual(set(tools), {"read_file", "grep_search", "list_directory"})

    def test_instruction_byte_budgets_are_not_token_claims(self):
        self.assertLessEqual((ROOT / "AGENTS.md").stat().st_size, 6000)
        for path in own_skills():
            self.assertLessEqual(path.stat().st_size, 3500)
        for path in (ROOT / "roles").glob("*.md"):
            self.assertLessEqual(path.stat().st_size, 2000)

    def test_operating_files_do_not_contain_machine_paths_or_model_matrix(self):
        roots = [ROOT / name for name in (".codex", ".claude", ".gemini", ".agents", "roles", "policies")]
        for directory in roots:
            for path in directory.rglob("*"):
                if path.is_file() and "worktrees" not in path.relative_to(ROOT).parts and not third_party(path):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotRegex(text, r"(?i)(?:(?<![a-z])[A-Z]:[\\/]|file:///|/Users/|/home/\w+/)")
                    if path.relative_to(ROOT).as_posix() == ".claude/agents/tinker-explorer.md":
                        # the one cost hint: the search-only Explorer (tier: light) runs on Claude's small model
                        self.assertEqual(re.findall(r"(?im)^\s*model\s*[:=].*$", text), ["model: haiku"])
                        continue
                    self.assertNotRegex(text, r"(?im)^\s*model\s*[:=]")

    def test_runtime_state_and_local_credentials_are_ignored(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        for pattern in (".tinker/", ".claude/settings.local.json", ".env", "__pycache__/"):
            self.assertIn(pattern, lines)

    def test_native_descriptors_resolve_all_four_canonical_charters(self):
        roles = {p.stem for p in (ROOT / 'roles').glob('*.md')}
        self.assertEqual(len(roles), 4)  # Lead is canonical AGENTS.md.
        for directory, suffix in (('.codex/agents', '.toml'), ('.claude/agents', '.md'),
                                  ('.agents/agents', '.md')):
            files = list((ROOT / directory).glob('tinker-*' + suffix))
            self.assertEqual({p.stem for p in files}, {'tinker-' + r for r in roles})
            for path in files:
                text = path.read_text(encoding='utf-8')
                if suffix == '.toml':
                    data = tomllib.loads(text)
                    self.assertEqual(data['agents'], {'enabled': False})
                    self.assertNotIn('model', data)
                    if data['sandbox_mode'] == 'read-only':
                        self.assertEqual(data['features'], {'shell_tool': False})
                    text = data['developer_instructions']
                self.assertIn('roles/' + path.stem.removeprefix('tinker-') + '.md', text)

    def test_antigravity_rule_import_resolves_and_readers_have_no_commands(self):
        rule = ROOT / '.agents/rules/tinker.md'
        text = rule.read_text()
        self.assertEqual(re.search(r'^trigger: (.+)$', text, re.M).group(1), 'always_on')
        target = re.search(r'^@(.+)$', text, re.M).group(1)
        self.assertEqual((rule.parent / target).resolve(), ROOT / 'AGENTS.md')
        for role in ('reviewer', 'researcher'):
            with self.subTest(role=role):
                reader = (ROOT / f'.agents/agents/tinker-{role}.md').read_text()
                self.assertEqual(set(re.findall(r'^  - (\w+)$', reader, re.M)),
                                 {'view_file', 'grep_search', 'find_by_name', 'list_dir'})
                self.assertRegex(reader, r'(?m)^commandExecutionPolicy: off$')

    def test_knowledge_candidate_template_has_schema(self):
        text = (ROOT / 'templates/candidate.md').read_text(encoding='utf-8')
        header = re.match(r'\A---\n(.*?)\n---\n', text, re.S).group(1)
        for key in ('candidate_id', 'repository', 'component', 'created_date', 'confidence'):
            self.assertRegex(header, rf'(?m)^{key}: \S')
        self.assertRegex(header, r'(?m)^status: candidate$')
        for section in ('Claim / Procedure', 'Observed Symptom & Provenance', 'Verification Evidence',
                        'Invalidation Conditions', 'Target Destination'):
            self.assertIn(f'\n## {section}\n', text)
        for target in ('`local-knowledge`', '`project-conventions`'):
            self.assertIn(target, text)

    def test_roles_carry_descriptor_front_matter(self):
        for path in (ROOT / 'roles').glob('*.md'):
            header = re.match(r'\A---\ndescription: (.+)\naccess: (read|write)\n(tier: light\n)?---\n',
                              path.read_text(encoding='utf-8'))
            self.assertIsNotNone(header, path)
            if header.group(3):
                self.assertEqual(header.group(2), 'read', path)

    def test_checkpoint_template_front_matter_is_what_hooks_read(self):
        text = (ROOT / 'templates/job.md').read_text(encoding='utf-8')
        header = re.match(r'\A---\n(.*?)\n---\n', text, re.S).group(1)
        self.assertEqual([line.split(':')[0] for line in header.splitlines()],
                         ['task_id', 'status', 'repository', 'worktree', 'host_session'])
        self.assertNotIn('- Status:', text)

    def test_no_skill_or_command_pins_a_model(self):
        files = own_skills() + list(ROOT.glob('commands/*.md')) + list(ROOT.glob('.claude/commands/*.md'))
        self.assertEqual(len(own_skills()), 7)
        for path in files:  # a model switch mid-chat drops the prompt cache; the user's model choice governs
            header = re.match(r'\A---\n(.*?)\n---\n', path.read_text(encoding='utf-8'), re.S)
            self.assertNotRegex(header.group(1) if header else '', r'(?m)^model\s*:', path)

    def test_checkpoint_handoff_carries_what_a_fresh_chat_needs(self):
        handoff = (ROOT / 'templates/job.md').read_text(encoding='utf-8').split('## Handoff', 1)[1]
        for field in ('- Last user request, word for word, and its status:', '- Tried and failed, each with the reason:',
                      '- Verify before trusting this handoff:', '- Previous chat:', 'never read it whole',
                      'starting point'):
            self.assertIn(field, handoff)

    def test_getting_started_and_evaluation_instructions_exist(self):
        for name in ("README.md", "docs/providers.md", "docs/extending.md", "evals/README.md"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_verification_recipe_and_domain_pack_templates_have_their_sections(self):
        recipe = (ROOT / 'templates/verification-recipe.md').read_text(encoding='utf-8')
        for section in ('Checkout and prerequisites', 'Environment and external dependencies',
                        'Startup and readiness', 'Test identity and data', 'Flow and expected outcome',
                        'Evidence and cleanup'):
            self.assertIn(f'\n## {section}\n', recipe)
        pack = (ROOT / 'templates/domain-pack.md').read_text(encoding='utf-8')
        header = re.match(r'\A---\n(.*?)\n---\n', pack, re.S).group(1)
        self.assertEqual([line.split(':')[0] for line in header.splitlines()],
                         ['pack_id', 'version', 'scope', 'owner', 'last_reviewed_date'])
        for section in ('Scope', 'Domain rules', 'Procedures', 'Pitfalls', 'Sources'):
            self.assertIn(f'\n## {section}\n', pack)

    def test_artifacts_write_markdown_first_and_change_remote_items_only_on_approval(self):
        skill = (ROOT / '.agents/skills/tinker-artifacts/SKILL.md').read_text(encoding='utf-8')
        agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('(.agents/skills/tinker-artifacts/SKILL.md)', agents)  # the Lead routes artifact requests
        for target in ('../../../templates/user-story.md', '../../../templates/adr.md'):
            self.assertIn(f'({target})', skill)
        self.assertIn('Markdown file', skill)  # the default destination
        for fmt in ('Mermaid', 'PlantUML', 'archify', 'ASCII'):
            self.assertIn(fmt, skill)
        # GitHub issues and boards come after the Markdown, gated on explicit approval; tools are never installed
        # and diagram source never goes to a public renderer.
        self.assertRegex(skill, r'(?s)GitHub issues.*explicit approval.*gh issue create')
        self.assertIn('Never send diagram source to a public rendering server or install a tool', skill)
        self.assertIn('`not-verified`', skill)
        story = (ROOT / 'templates/user-story.md').read_text(encoding='utf-8')
        self.assertRegex(story, r'\*\*As a\*\*.*\*\*I want\*\*.*\*\*so that\*\*')
        self.assertIn('\n## Acceptance criteria\n', story)
        self.assertRegex(story, r'\*\*Given\*\*.*\*\*when\*\*.*\*\*then\*\*')
        adr = (ROOT / 'templates/adr.md').read_text(encoding='utf-8')
        for section in ('Context', 'Options considered', 'Decision', 'Consequences'):
            self.assertIn(f'\n## {section}\n', adr)

    def test_workflows_share_the_application_verification_reference(self):
        for skill in ('implement', 'investigate', 'review'):
            text = (ROOT / f'.agents/skills/tinker-{skill}/SKILL.md').read_text(encoding='utf-8')
            self.assertIn('../../../policies/app-verification.md', text, skill)

    def test_routine_templates_fit_the_schedule_plan_subset(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        try:
            tinker_runtime = importlib.import_module('tinker_runtime')
        finally:
            sys.path.remove(str(ROOT / 'scripts'))
        text = (ROOT / 'templates/routines.md').read_text(encoding='utf-8')
        plans = re.findall(r'`(schedule-plan [^`]+)`', text)
        self.assertEqual(len(plans), 2)
        for plan in plans:  # schedule-plan refuses a plan without any of these
            for option in ('--app', '--role', '--repo', '--cron', '--task'):
                self.assertIn(option, plan)
        crons = [cron for cron in re.findall(r'--cron "([^"]+)"', text) if not cron.startswith('<')]
        self.assertEqual(len(crons), 1)
        for task in re.findall(r'- Task: (.*?)(?=\n\n|\nIn Claude|\Z)', text, re.S):
            self.assertLessEqual(len(' '.join(task.split())), 500)  # schedule-plan keeps one line of 500
        for cron in crons:
            self.assertTrue(tinker_runtime.cron_to_rrule(cron).startswith('FREQ='), cron)

    def test_core_has_no_builtin_product_or_team_registry(self):
        for name in ('config/repositories.json', 'config/teams.json', 'repos', 'teams'):
            with self.subTest(path=name):
                self.assertFalse((ROOT / name).exists(),
                                 f'{name} selects products or teams: keep organization guidance outside the core')

    def test_workflows_start_from_the_playbook_and_end_with_a_retro(self):
        for skill in ('implement', 'investigate', 'review', 'shape'):
            text = (ROOT / f'.agents/skills/tinker-{skill}/SKILL.md').read_text(encoding='utf-8')
            self.assertIn('../../../policies/retro.md', text, skill)
        for skill in ('implement', 'investigate'):
            text = (ROOT / f'.agents/skills/tinker-{skill}/SKILL.md').read_text(encoding='utf-8')
            self.assertIn('../../../policies/workspace.md#task-start', text, skill)
        workspace = (ROOT / 'policies/workspace.md').read_text(encoding='utf-8')
        self.assertIn('\n## Task start\n', workspace)
        # rebase only a clean, unpushed branch; never stash or force-push to catch up
        self.assertIn('--untracked-files=no', workspace)
        self.assertIn('rev-list --count HEAD --not --remotes', workspace)
        self.assertIn('never stash, rebase or\nforce-push', workspace)
        retro = (ROOT / 'policies/retro.md').read_text(encoding='utf-8')
        for anchor in ('# Retro\n', '.tinker/retros/', '`round`', 'no secrets'):
            self.assertIn(anchor, retro)
        learning = (ROOT / 'policies/learning.md').read_text(encoding='utf-8')
        for anchor in ('\n## Learn\n', 'tinker/learn-', 'heldout'):
            self.assertIn(anchor, learning)
        playbook = (ROOT / 'templates/agent-playbook.md').read_text(encoding='utf-8')
        self.assertIn('## Agent playbook', playbook)
        for line in ('Base branch:', 'Gates', 'Deliverable and commits:', 'Worktrees:', 'Live pass:', 'Graph:',
                     'Pitfalls:'):
            self.assertIn(f'- {line}', playbook)

    def test_shape_has_a_grill_mode_and_implement_a_minimalism_ladder(self):
        shape = (ROOT / '.agents/skills/tinker-shape/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('\n## Grill mode\n', shape)
        self.assertIn('one decision at a time', shape.replace('\n', ' '))
        self.assertIn('Change nothing until the user confirms', shape.replace('\n', ' '))
        implement = (ROOT / '.agents/skills/tinker-implement/SKILL.md').read_text(encoding='utf-8')
        flat = ' '.join(implement.split())
        self.assertIn('Never add a dependency', flat)
        self.assertIn('never trim validation, error handling', flat)

    def test_claude_project_settings_deny_destructive_git_for_both_shells(self):
        settings = json.loads((ROOT / '.claude/settings.json').read_text(encoding='utf-8'))
        deny, ask = settings['permissions']['deny'], settings['permissions']['ask']
        for pattern in ('git *push*--force*', 'git *reset*--hard*', 'git clean -*', 'git restore *',
                        'git *branch* -D *', 'git *stash clear*', 'git *worktree remove*--force*'):
            for tool in ('Bash', 'PowerShell'):
                self.assertIn(f'{tool}({pattern})', deny)
        # Claude Code shows an ask rule's prompt even in bypass mode, where the user chose no prompts.
        self.assertEqual(ask, [])
        # A rule ending in `:*` is the legacy prefix form, whose other `*` match literally.
        self.assertFalse([rule for rule in deny if rule.endswith(':*)')], deny)
        for command in ('git push origin --delete feat', 'git push origin -d feat', 'git push origin :feat'):
            self.assertFalse([rule for rule in deny if fnmatch.fnmatchcase(f'Bash({command})', rule)], command)
        env = settings['env']
        self.assertEqual(env['PLAYWRIGHT_MCP_ISOLATED'], 'true')
        for origin in env['PLAYWRIGHT_MCP_ALLOWED_ORIGINS'].split(';'):
            self.assertRegex(origin, r'^https?://(localhost|127\.0\.0\.1):\*$')  # a live pass stays local
        self.assertFalse(Path(env['PLAYWRIGHT_MCP_OUTPUT_DIR']).is_absolute())

    def test_external_workers_are_opt_in_sandboxed_and_reached_from_delegation(self):
        policy_path, brief_path = ROOT / 'policies/external-workers.md', ROOT / 'templates/worker-brief.md'
        policy = policy_path.read_text(encoding='utf-8')
        flat = ' '.join(policy.split())
        # AGENTS.md stays as it is, so this delegation line is the only route to the policy
        delegation = ' '.join((ROOT / 'policies/delegation.md').read_text(encoding='utf-8').split())
        self.assertIn('When the user says to use, consult or parallelize with Codex, follow '
                      '[external workers](external-workers.md).', delegation)
        self.assertIn('(../templates/worker-brief.md)', policy)
        self.assertTrue(brief_path.is_file())
        self.assertTrue(' '.join(brief_path.read_text(encoding='utf-8').split('\n---\n', 1)[1].split()).startswith(
            'You are a worker: print no Triage line, write no retro or checkpoint, spawn no helpers, never run codex'))
        for phrase in ('"consult Codex"', '"use Codex too for these tasks"', '"parallelize with Codex"',
                       'never automatic', 'never by quota', "never on the Lead's own initiative"):
            self.assertIn(phrase, flat)
        readme = ' '.join((ROOT / 'README.md').read_text(encoding='utf-8').split())
        self.assertIn('(policies/external-workers.md)', readme)
        for phrase in ('"consult Codex"', '"use Codex too for these tasks"', '"parallelize with Codex"'):
            self.assertIn(phrase, readme)
        commands = [' '.join(block.replace('\\\n', ' ').split())
                    for block in re.findall(r'```sh\n(.*?)```', policy, re.S) if 'codex exec' in block]
        self.assertEqual([('-s read-only' in c, '-s workspace-write' in c) for c in commands],
                         [(True, False), (False, True)])
        for command in commands:
            for flag in ('--ignore-user-config', '-c approval_policy=never', '-c model_reasoning_effort=medium',
                         ' -C <', '--json', ' -o <', '--ephemeral', ' - <'):
                self.assertIn(flag, command)
            for flag in (' -m ', '--model', '--add-dir', '--dangerously', '--trust', '--worktree'):
                self.assertNotIn(flag, command)
        for flag in ('--add-dir', '--dangerously-bypass-approvals-and-sandbox', '--dangerously-bypass-hook-trust'):
            self.assertRegex(flat, rf'Never pass [^.]*`{flag}`')

    def test_external_worker_change_names_no_model_or_user_profile_path(self):
        for name in ('policies/external-workers.md', 'templates/worker-brief.md', 'policies/delegation.md',
                     'docs/providers.md', 'docs/architecture.md', 'docs/history.md', 'README.md'):
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'(?i)\bgpt[-_]', name)
            self.assertNotRegex(text, r'(?i)\b[a-z]:[\\/]+users\b', name)

    def test_front_door_lists_its_forms_and_routes_through_the_lead(self):
        text = (ROOT / '.agents/skills/tinker/SKILL.md').read_text(encoding='utf-8')
        for form in ('`<task>`', 'No task', '`status`', '`reload [path ...]`', '`remember <fact>`', '`learn [focus]`',
                     '`eval [args]`', '`playbook <repo>`', '`schedule <what> <when>`', '`help`'):
            self.assertIn(f'\n## {form}\n', text)
        self.assertIn("question route, with no workflow skill", ' '.join(text.split()))
        self.assertIn('(../../../AGENTS.md)', text)
        self.assertIn('(.agents/skills/tinker/SKILL.md)', (ROOT / 'AGENTS.md').read_text(encoding='utf-8'))


if __name__ == "__main__":
    unittest.main()
