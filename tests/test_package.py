"""Structural checks only: these do not establish live model compliance."""
import importlib
import json
from pathlib import Path
import re
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".tinker", "__pycache__"}


def package_files():
    worktrees = ROOT / ".claude" / "worktrees"  # ignored linked worktrees hold whole other copies of the package
    return [p for p in ROOT.rglob("*") if p.is_file() and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
            and not p.is_relative_to(worktrees)]


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

    def test_eight_unique_discoverable_skills(self):
        skills = list((ROOT / ".agents/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 8)
        self.assertEqual(len([p for p in package_files() if p.name == "SKILL.md"]), 8)
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

    def test_codex_concurrency_setting_has_no_model_override(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
        self.assertEqual(config, {"agents": {"max_concurrent_threads_per_session": 2}})

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
        for path in (ROOT / ".agents/skills").glob("*/SKILL.md"):
            self.assertLessEqual(path.stat().st_size, 3500)
        for path in (ROOT / "roles").glob("*.md"):
            self.assertLessEqual(path.stat().st_size, 2000)

    def test_operating_files_do_not_contain_machine_paths_or_model_matrix(self):
        roots = [ROOT / name for name in (".codex", ".claude", ".gemini", ".agents", "roles", "policies")]
        for directory in roots:
            for path in directory.rglob("*"):
                if path.is_file() and "worktrees" not in path.relative_to(ROOT).parts:
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

    def test_cases_have_unique_identity_and_reviewable_contracts(self):
        cases = json.loads((ROOT / "evals/cases.json").read_text())
        self.assertGreaterEqual(len(cases), 14)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for case in cases:
            self.assertTrue(case["prompt"] and case["setup"] and case["manual_review"])
            fields = [rule["field"] for rule in case["rules"]]
            self.assertEqual(len(fields), len(set(fields)))
            self.assertIn("peak_active_helpers", fields)
            self.assertIn("peak_active_writers", fields)

    def test_native_descriptors_resolve_all_nine_canonical_charters(self):
        roles = {p.stem for p in (ROOT / 'roles').glob('*.md')}
        self.assertEqual(len(roles), 9)  # Lead is canonical AGENTS.md.
        for directory, suffix in (('.codex/agents', '.toml'), ('.claude/agents', '.md'),
                                  ('.agents/agents', '.md')):
            files = list((ROOT / directory).glob('*' + suffix))
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
        for role in ('reviewer', 'researcher', 'product-manager', 'designer'):
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
        self.assertEqual(len(plans), 3)
        for plan in plans:  # schedule-plan refuses a plan without any of these
            for option in ('--app', '--role', '--repo', '--cron', '--task'):
                self.assertIn(option, plan)
        crons = re.findall(r'--cron "([^"]+)"', text)
        self.assertEqual(len(crons), 3)
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
            self.assertIn('../../../policies/learning.md#retro', text, skill)
        for skill in ('implement', 'investigate'):
            text = (ROOT / f'.agents/skills/tinker-{skill}/SKILL.md').read_text(encoding='utf-8')
            self.assertIn('../../../policies/workspace.md#task-start', text, skill)
        workspace = (ROOT / 'policies/workspace.md').read_text(encoding='utf-8')
        self.assertIn('\n## Task start\n', workspace)
        # rebase only a clean, unpushed branch; never stash or force-push to catch up
        self.assertIn('--untracked-files=no', workspace)
        self.assertIn('rev-list --count HEAD --not --remotes', workspace)
        self.assertIn('never stash, rebase or\nforce-push', workspace)
        learning = (ROOT / 'policies/learning.md').read_text(encoding='utf-8')
        for anchor in ('\n## Retro\n', '\n## Learn\n', '.tinker/retros/', 'tinker/learn-', 'heldout'):
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
                        'git *branch* -D *', 'git *stash drop*', 'git *worktree remove*--force*'):
            for tool in ('Bash', 'PowerShell'):
                self.assertIn(f'{tool}({pattern})', deny)
        self.assertIn('Bash(git *push*--delete*)', ask)
        env = settings['env']
        self.assertEqual(env['PLAYWRIGHT_MCP_ISOLATED'], 'true')
        for origin in env['PLAYWRIGHT_MCP_ALLOWED_ORIGINS'].split(';'):
            self.assertRegex(origin, r'^https?://(localhost|127\.0\.0\.1):\*$')  # a live pass stays local
        self.assertFalse(Path(env['PLAYWRIGHT_MCP_OUTPUT_DIR']).is_absolute())

    def test_front_door_lists_its_forms_and_routes_through_the_lead(self):
        text = (ROOT / '.agents/skills/tinker/SKILL.md').read_text(encoding='utf-8')
        for form in ('`<task>`', 'No task', '`status`', '`remember <fact>`', '`learn [focus]`', '`eval [args]`',
                     '`playbook <repo>`', '`schedule <what> <when>`', '`help`'):
            self.assertIn(f'\n## {form}\n', text)
        self.assertIn("question route, with no workflow skill", ' '.join(text.split()))
        self.assertIn('(../../../AGENTS.md)', text)
        self.assertIn('(.agents/skills/tinker/SKILL.md)', (ROOT / 'AGENTS.md').read_text(encoding='utf-8'))


if __name__ == "__main__":
    unittest.main()
