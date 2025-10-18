# Using GitHub Actions to run sync jobs and secure environment variables

This document explains how to configure GitHub Actions workflows to run synchronization code (a "sync" job), and how to use GitHub Secrets and Environments for secure configuration instead of committing a `.env` file.

Contents
- Overview
- Recommended workflow location
- Example sync workflow (Node.js and generic)
- How to replace .env with GitHub Secrets and Environments
- Best practices and security recommendations
- Troubleshooting checklist

---

## Overview

Instead of storing sensitive values in a repository file (like `.env`), use GitHub Secrets and Environments. A workflow can access secrets at runtime and pass them to your sync job as environment variables without writing them into source control.

Typical sync job tasks:
- Checkout repository
- Install dependencies (Node/Python/Go/etc.)
- Authenticate to external services (databases, cloud storage, other repos)
- Run your sync script (e.g., `npm run sync`, `python sync.py`)
- Optionally push results somewhere (use carefully scoped tokens)

---

## Recommended workflow location

Place workflows under:
`.github/workflows/` — for example:
`.github/workflows/sync.yml`

Workflows can be triggered on pushes, schedules, or manual dispatches (workflow_dispatch).

---

## Example: Node.js sync workflow (recommended pattern)

This example shows a job that runs a sync script using secrets (no committed `.env` file). It sets environment variables for the step and does not print secrets.

```yaml
name: Sync Job

on:
  push:
    branches: [ main ]
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * *' # optional daily at 03:00 UTC

jobs:
  sync:
    runs-on: ubuntu-latest
    # Optionally bind to a GitHub Environment (see "Environments" section below)
    environment: production

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Use Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run sync script
        env:
          # Reference repository or environment secrets here:
          API_KEY: ${{ secrets.API_KEY }}
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASS: ${{ secrets.DB_PASS }}
        run: |
          # Child process (Node) will see the env vars at runtime
          npm run sync
```

Notes:
- Do not echo or write secrets to the workflow log.
- Use `env:` in a step to pass secrets to the runtime process.
- If you must create a file (e.g., `.env`) for a library that only reads files, do so carefully and delete it immediately after use:
  - Use temporary file creation.
  - Avoid adding this file to artifacts or repo.
  - Example (less preferred):
    run: |
      cat > .env <<EOF
      DB_HOST=${{ secrets.DB_HOST }}
      DB_USER=${{ secrets.DB_USER }}
      DB_PASS=${{ secrets.DB_PASS }}
      EOF
      npm run sync
      shred -u .env || rm .env

---

## Example: Generic / Python sync workflow

```yaml
name: Python Sync

on:
  workflow_dispatch:
  schedule:
    - cron: '0 4 * * *'

jobs:
  sync:
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run sync
        env:
          SECRET_TOKEN: ${{ secrets.SECRET_TOKEN }}
        run: python sync.py
```

---

## How to replace `.env` with GitHub Secrets and Environments

1. Add secrets:
   - Repository-level: Settings → Secrets and variables → Actions → New repository secret.
   - Environment-level (preferred for deploy secrets): Settings → Environments → create an environment (e.g., `production`), then add secrets there.

2. Reference secrets in the workflow:
   - As step environment variables:
     env:
       MY_SECRET: ${{ secrets.MY_SECRET }}
   - Or directly in commands (not recommended to echo):
     run: some-command --token "${{ secrets.MY_SECRET }}"

3. Use GitHub Environments for extra protection:
   - Create an environment (Settings → Environments).
   - Add environment-level secrets (they are accessed in the same way: `${{ secrets.NAME }}` when the job uses `environment: my-environment`).
   - Add protection rules, e.g., required reviewers for deployments, wait timers, branch restrictions.

4. Prefer passing secrets as environment variables rather than writing a `.env` file. If a third-party tool mandates a file, create it at runtime and delete it immediately, keeping it out of logs and artifacts.

---

## Using tokens to push or access other repos/services

- Use the automatically provided `GITHUB_TOKEN` for repository API actions. It has limited, scoped permissions:
  - Example: push status or create a PR with `GITHUB_TOKEN` (note workflow must have permission to write).
- For cross-repo pushes or external services, create a short-lived personal access token (PAT) with least privileges and store it as a secret (or use OIDC where available).
- Example of using PAT:
  env:
    PAT: ${{ secrets.PAT_PUSH }}
  run: |
    git remote set-url origin https://x-access-token:${PAT}@github.com/owner/repo.git
    git push ...

---

## Best practices and security recommendations

- Never commit `.env` with secrets to the repo.
- Use environment-level secrets for production deploys so they are only exposed to jobs tied to that environment.
- Avoid printing secret values in logs. Masked secrets are safe in logs, but don't intentionally print them.
- Use least privilege for tokens. Prefer short-lived keys and rotate them regularly.
- Use GitHub Environments protections: required reviewers for production, wait timers, or IP allow lists if available.
- Limit workflow triggers that have access to secrets (e.g., avoid running secret-using workflows on pull requests from forks).
  - By default, secrets are not available to workflows triggered from pull requests from forks — that's a safety benefit.
- Audit secret usage and rotate secrets if you detect leaks or after a person with access leaves.

---

## Example: Protecting deployment with required reviewers

1. Create environment `production` in repository settings.
2. Enable protection rules and add one or more reviewers.
3. In your workflow:
   jobs:
     deploy:
       environment: production
       steps:
         ...

The job will pause and require reviewer approval before it receives environment secrets.

---

## Troubleshooting checklist

- If a secret appears empty in the runner:
  - Confirm it exists at the repository or environment scope.
  - Confirm the job references the proper environment (if secret is environment-scoped).
  - Check that the workflow trigger is allowed to access secrets (forked PRs won't have repository secrets).
- If a job fails to push:
  - Verify token permissions (push requires appropriate repo scope).
  - Review `GITHUB_TOKEN` or PAT usage.
- If sync is failing:
  - Run the sync script locally with the same env vars to reproduce.
  - Add a debug step that prints non-sensitive status (avoid secrets).

---

## Summary

- Use GitHub Actions to run sync jobs, triggered by push/schedule/manual.
- Replace `.env` with GitHub Secrets and/or Environment-level secrets.
- Pass secrets as `env:` in steps or use them directly in commands — avoid writing secrets into repo.
- Use Environments to protect production secrets and require approvals where necessary.
- Follow least privilege, rotate secrets, and avoid printing secrets in logs.

If you'd like, I can:
- Create the workflow file (e.g., `.github/workflows/sync.yml`) using the example above tailored to your project's language and sync command.
- Open a PR adding this documentation to `docs/GITHUB_ACTIONS_SYNC.md`.
