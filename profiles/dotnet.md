# C# / .NET profile

Apply only to .NET work, after reading the target framework, language version,
nullable settings, `.editorconfig` and established conventions. Do not upgrade
the runtime or rewrite older code merely to follow this profile.

- Prefer `var` when it aids clarity and follows local style.
- Use nullable reference types where supported; handle absence explicitly.
- Keep asynchronous flows asynchronous; avoid blocking on tasks. Propagate
  cancellation where operations and APIs support it.
- Use established dependency injection and cohesive, focused interfaces.
- Prefer testable boundaries and behavioral tests in the repository's framework.
- Use modern C# features consistent with the target runtime and surrounding code.
- Avoid unnecessary service/repository wrappers and interfaces for every class.
- Before tests, check symbols and types by building the changed project with
  `dotnet build -v minimal --no-incremental` ([tool guidance](../policies/tools.md)).
- Verify changed projects/tests with relevant filters; inspect actual test counts.
  Do not assume a solution build executes tests or that every project uses the
  same SDK/test runner.
