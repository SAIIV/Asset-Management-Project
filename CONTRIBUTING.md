# Contributing Guide

This guide provides a simple workflow for team members who are new to Git and GitHub. Each member should use their own GitHub account and make their own commits so that contribution history remains accurate.

## One-time setup

1. Install Git and sign in to your own GitHub account.
2. Clone the repository to your computer.
3. Configure Git with your own name and an email connected to your GitHub account:

```bash
git config user.name "Your Name"
git config user.email "your-email@example.com"
```

Do not share GitHub accounts, passwords, access tokens, or one person's local repository between team members.

## Starting a task

Before beginning new work, update your copy of the main branch and create a separate branch:

```bash
git switch main
git pull
git switch -c docs/short-task-name
```

Recommended branch prefixes:

- `docs/` for reports, requirements, diagrams, and meeting notes
- `feat/` for a new system feature
- `fix/` for a correction
- `test/` for test cases or automated tests

Examples include `docs/stakeholder-analysis` and `feat/asset-registration`.

## Saving your work

Keep each commit focused on one meaningful change:

```bash
git status
git add path/to/changed-file
git commit -m "docs: add stakeholder analysis"
git push -u origin docs/short-task-name
```

Good commit messages describe the completed change:

- `docs: document asset transfer workflow`
- `feat: add asset registration form`
- `test: add reservation validation cases`
- `fix: prevent duplicate asset requests`

Avoid unclear messages such as `update`, `changes`, `work`, or `final`.

## Opening a pull request

After pushing a branch:

1. Open the repository on GitHub.
2. Select **Compare & pull request**.
3. Explain what you changed and how it was checked.
4. Ask another team member to review it.
5. Address feedback with additional commits on the same branch.
6. Merge only after the work is ready.

Do not commit directly to `main` once the team begins collaborating unless the group has agreed that the change is a small emergency correction.

## Document collaboration

- Assign a clear owner to each section.
- Record joint decisions in meeting notes.
- Do not replace another member's work without discussing it.
- Preserve meaningful commit history when combining sections.
- Review the final document as a group before submission.

## Before submitting a pull request

- Confirm that your name and email belong to your own GitHub account.
- Review every changed file.
- Remove personal data, passwords, keys, and temporary files.
- Check spelling, formatting, links, and document consistency.
- Make sure the change belongs to the correct phase folder.
