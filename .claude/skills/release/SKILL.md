---
name: release
description: >-
  End-to-end release workflow for iscc-tika. Bumps version, runs quality gates,
  commits, creates PR to main, and publishes Python wheels to PyPI.
  Self-healing: diagnoses and fixes failures before retrying.
disable-model-invocation: false
user-invocable: true
argument-hint: <version> [--dry-run] [--skip-publish]
---

# Release Workflow for iscc-tika

Execute a robust, self-healing release workflow. The version argument is required.

**Invocation:** `/release 0.3.0` or `/release 0.3.0 --dry-run`

**Flags:**

- `--dry-run` — run all checks but do NOT commit, push, create PR, tag, or publish. Reports what
    would happen at each skipped step
- `--skip-publish` — do everything through PR merge but do NOT trigger the release workflow

## Phase 1: Pre-flight Checks

Before touching anything, validate the environment is ready.

**Required tools:** `git`, `gh` (authenticated), `mise`, `cargo`, `python`, `curl`.

### Step 1.1 — Parse arguments

Extract the version from `$ARGUMENTS`. It must be a valid semver string (e.g., `0.3.0`, `0.4.1`,
`1.0.0`). Detect `--dry-run` and `--skip-publish` flags if present.

If no version is provided, stop and ask the user for one.

### Step 1.2 — Branch and working tree

```
git status
git branch --show-current
```

- Must be on `develop` branch
- Working tree must be clean (no uncommitted changes). Untracked files in `.claude/` are OK
- If there are uncommitted changes, list them and ask the user whether to stash or abort

### Step 1.3 — Pull latest

```
git pull --ff-only
```

If this fails (diverged history), stop and explain the situation.

### Step 1.4 — Current version check

Read the current version from `iscc-tika-core/Cargo.toml` (the `version` field under `[package]`).
Verify the requested version is strictly higher than the current version (compare major.minor.patch
numerically). If not, stop and explain.

### Step 1.5 — CI status

Check that the latest CI workflow run on `develop` is passing:

```
gh run list --workflow ci.yml --branch develop --limit 1 --json status,conclusion,headSha
```

If CI is not green, warn the user and ask whether to proceed anyway.

## Phase 2: Version Bump

### Step 2.1 — Update versions in both manifests

Two files must be updated:

1. `iscc-tika-core/Cargo.toml` — the `version` field under `[package]`
2. `bindings/iscc-tika-python/pyproject.toml` — the `version` field under `[project]`

Edit both files to set the new version.

### Step 2.2 — Update Cargo.lock

```
cargo check --manifest-path iscc-tika-core/Cargo.toml
```

This regenerates the lockfile entry for `iscc-tika` with the new version. Do NOT use `cargo update`
which can also upgrade external dependency versions.

### Step 2.3 — Validate consistency

```
mise run version:check
```

Both versions must match. If there is a mismatch, diagnose and fix, then re-run the check.

## Phase 3: Quality Gates

### Step 3.1 — Format

```
mise run format
```

This applies all pre-commit auto-fix hooks. If it modifies files, that's expected — the changes will
be included in the release commit.

### Step 3.2 — Lint

```
mise run lint
```

If linting fails:

1. Read the error output carefully
2. Attempt to fix the issues (formatting, clippy warnings, ruff violations). Lint fixes triggered by
    quality gates are within scope of the release — they are not "edits outside version scope"
3. Re-run `mise run lint`
4. If it fails again after one fix attempt, stop and show the errors to the user

### Step 3.3 — Test

```
mise run test
```

If tests fail:

1. Read test output to identify the failing test(s)
2. Determine if the failure is related to the version bump (unlikely) or a pre-existing issue
3. If pre-existing: warn the user and ask whether to proceed
4. If version-related: attempt to fix, re-run tests
5. If tests fail twice, stop and show the errors to the user

## Phase 4: Commit and Push

### Step 4.1 — Stage release changes

Stage only the files modified by the version bump and quality gates. Use `git diff --name-only` to
find which files were actually modified, then stage only those. Expected candidates:

```
iscc-tika-core/Cargo.toml
iscc-tika-core/Cargo.lock
bindings/iscc-tika-python/pyproject.toml
```

Do NOT use `git add -A` which can stage untracked files from `.claude/` and other directories.
Review staged files with `git status` before committing.

### Step 4.2 — Commit

If `--dry-run`, skip this step and Step 4.3. Report staged files and what the commit message would
be, then skip to Phase 6 (which also checks for `--dry-run`).

Create the release commit. Use the exact format:

```
git commit -m "$(cat <<'EOF'
Release <version>
EOF
)"
```

### Step 4.3 — Push develop

If `--dry-run`, skip (already handled in Step 4.2).

```
git push origin develop
```

If push fails due to pre-push hooks:

1. Read the hook output
2. Fix the issue (likely a formatting or test failure)
3. Stage the fix and create a new commit (do NOT amend — the failed push means the commit exists
    locally)
4. Retry push
5. If it fails twice, stop and show the errors

## Phase 5: PR and Merge

If `--dry-run`, skip this phase entirely and summarize what would happen.

### Step 5.1 — Create or update PR

Check if a PR from `develop` to `main` already exists:

```
gh pr list --head develop --base main --json number,state,url
```

If a PR exists and is open, report its URL. If no PR exists, create one:

```
gh pr create -B main -H develop --title "Release <version>" --body "$(cat <<'EOF'
## Release <version>

Version bump for release <version>.

Publishes to: PyPI (Linux x86_64, macOS x86_64/aarch64, Windows x64).
EOF
)"
```

### Step 5.2 — Wait for CI

Watch PR checks until they complete:

```
gh pr checks <pr-number> --watch --fail-fast
```

This blocks until all checks finish (exit 0 = all passed, exit 1 = failure, exit 8 = pending
timeout). If CI fails, show which check failed and stop.

### Step 5.3 — Ask to merge

**Do NOT merge automatically.** Ask the user:

> PR #N is green and ready to merge: <url>. Shall I merge it?

Wait for explicit confirmation. Always use a **merge commit** (never squash or rebase — those
rewrite history and cause divergence on the long-lived `develop` branch):

```
gh pr merge <pr-number> --merge
```

(The default is to not delete the branch, which is what we want — `develop` stays alive.)

## Phase 6: Trigger Release Workflow

If `--dry-run`, skip this phase entirely. Report a dry-run summary: version bump was applied to
working tree files but not committed (Step 4.2 skipped the commit). The user can inspect the changes
with `git diff` and discard them with `git checkout -- .` if desired. Then jump to the final summary
(Phase 7 also skips in dry-run).

### Step 6.1 — Trigger the release workflow

If `--skip-publish`, skip this step and Step 6.2. Report that the PR was merged and the release can
be triggered later with `gh workflow run release.yml --ref main -f version=<version>`.

Trigger the release workflow via `workflow_dispatch`. The workflow handles everything: building
Python wheels for all platforms, running smoke tests, and publishing to PyPI.

```
gh workflow run release.yml --ref main -f version=<version>
```

Wait a few seconds for the run to appear, then find it:

```
gh run list --workflow release.yml --event workflow_dispatch --limit 1 --json databaseId,status,conclusion,url
```

### Step 6.2 — Monitor release workflow

Once the run is found, watch it:

```
gh run watch <databaseId>
```

Report progress. If the workflow fails, show the URL and which job failed.

### Step 6.3 — Switch back to develop

```
git checkout develop
git pull --ff-only
```

Ensure develop is up to date after the merge.

## Phase 7: Post-Release Verification

If `--dry-run` or `--skip-publish`, skip this phase.

### Step 7.1 — Verify registries

After the release workflow completes, verify PyPI has the new version:

```
curl -sf "https://pypi.org/pypi/iscc-tika/<version>/json" > /dev/null && echo "PyPI: OK" || echo "PyPI: NOT FOUND"
```

If it shows "NOT FOUND" but the release workflow succeeded, it may take a few minutes for the
registry to index. Suggest re-checking later.

### Step 7.2 — Summary

Print a final summary:

```
Release <version> complete!

  Commit:   <sha>
  PR:       <url>

  Registry:
    PyPI               <version>  OK

  Verify installation:
    pip install iscc-tika==<version>
```

## Self-Healing Rules

When any step fails:

1. **Read the full error output** — don't guess what went wrong
2. **Identify the root cause** — is it a code issue, environment issue, or transient failure?
3. **Attempt one fix** — apply the most likely fix and retry the step
4. **If the fix doesn't work, stop** — show the error to the user and ask for guidance
5. **Never retry more than twice** — infinite retry loops waste time
6. **Never skip a failing step silently** — every failure must be reported
7. **Never force-push or use destructive git operations** — ask the user first

## Re-triggering PyPI Publish

If the release workflow fails during PyPI publishing (while wheel builds succeeded), the publish can
be re-triggered via `workflow_dispatch` without the `version` input:

```
gh workflow run release.yml --ref main -f pypi=true
```

**Critical:** Always use `--ref main`. Do NOT pass `-f version=<version>` for re-triggers — that
would re-run version validation unnecessarily.

The publish step has a version-existence check that skips already-published versions (idempotent).

## Important Constraints

- This skill handles real releases with real side effects. Be careful and precise
- Never guess registry credentials or authentication — PyPI uses a `PYPI_TOKEN` secret configured in
    GitHub Actions
- Never modify files outside the release scope without asking. Release scope includes: version bump
    files, formatting/lint fixes from quality gates, and any files the pre-commit hooks auto-fix
- The `develop` branch is never deleted — it's the long-lived working branch
