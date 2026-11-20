# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues. Use the `gh` CLI for operations. Infer the repository from the git remote.

## Conventions

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --json number,title,body,labels,comments`
- List: `gh issue list --state open`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: comment with the resolution, then `gh issue close <number>`.
- Link blockers with GitHub issue dependencies when available; otherwise add `Blocked by: #<n>` to the issue body.
- Keep issues in `ric6121824/LightlessGroupExaminer`. PRs are not a triage request surface.
