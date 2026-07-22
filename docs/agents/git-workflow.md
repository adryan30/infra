# Git workflow (Argo CD)

`main` is live: Argo CD auto-syncs the App-of-apps chart from this repository’s default branch. A commit that reaches `main` can change the cluster immediately.

## Rules for agents

- **Never commit to `main`.** Create a feature branch, commit there, push the branch, and open a PR with `gh pr create`.
- **Never push to `main`** (including merge commits made locally). Merge via the GitHub PR UI / `gh pr merge` only when the user asks.
- If you accidentally committed on `main` and have **not** pushed: move the commits onto a new branch (`git branch <name>`, then `git reset --hard origin/main`), push the branch, and open a PR.
- If you have already pushed to `main`, stop and tell the user — do not force-push `main` unless they explicitly request it.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional-scope>): <description>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.

- Imperative, concise description; focus on why when a body is needed.
- Scope is optional (e.g. `feat(vault): …`, `docs(agents): …`).
- Repo merges to `main` via **squash only** — the PR title becomes the squash commit; keep it conventional too.
