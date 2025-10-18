# Using GitHub Actions for Automated Scrobbling

This guide explains how to configure and use GitHub Actions to automatically run the YouTube Music scrobbling script. It covers setting up secrets, configuring the workflow, and best practices for security and reliability.

## Overview

Instead of running the scrobbler manually, you can use a GitHub Actions workflow to run it on a schedule. This automates the process of fetching your YouTube Music history and scrobbling it to Last.fm. To do this securely, we will use GitHub Secrets to store your sensitive information (like API keys and cookies) instead of committing them to the repository in a `.env` file.

The workflow will:
- Run on a schedule (e.g., daily).
- Check out the repository code.
- Set up a Python environment.
- Install the required dependencies.
- Run the scrobbling script using your secrets as environment variables.

## 1. Configuring Secrets

You need to add the following secrets to your GitHub repository so the workflow can access them. It is recommended to use **Environment-Level Secrets** for better security.

### Required Secrets

-   `LAST_FM_API_KEY`: Your Last.fm API key.
-   `LAST_FM_API_SECRET`: Your Last.fm API secret.
-   `LASTFM_SESSION_KEY`: Your Last.fm session key.
-   `YTMUSIC_COOKIE`: Your YouTube Music cookie.
-   `DISCORD_WEBHOOK_URL`: Your Discord webhook URL for notifications.

### How to Add Secrets

1.  **Navigate to your repository on GitHub.**
2.  Click on **Settings**.
3.  In the left sidebar, click on **Environments**.
4.  Click on **New environment** and name it `production`.
5.  In the `production` environment, click on **Add secret** for each of the secrets listed above.
6.  Enter the name of the secret (e.g., `LAST_FM_API_KEY`) and its value.
7.  Click on **Add secret**.

## 2. The GitHub Actions Workflow

The following workflow is defined in `.github/workflows/sync.yml`. It is already configured to work with the secrets you've just added.

```yaml
name: Sync Job

on:
  push:
    branches: [ main ]
  workflow_dispatch:
  schedule:
    - cron: '0 23 * * *' # Runs daily at 23:00 UTC

jobs:
  sync:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run sync script
        env:
          LAST_FM_API_KEY: ${{ secrets.LAST_FM_API_KEY }}
          LAST_FM_API_SECRET: ${{ secrets.LAST_FM_API_SECRET }}
          LASTFM_SESSION_KEY: ${{ secrets.LASTFM_SESSION_KEY }}
          YTMUSIC_COOKIE: ${{ secrets.YTMUSIC_COOKIE }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python start.py
```

### How it Works

-   **`on`**: This section defines when the workflow will run. It's configured to run on pushes to the `main` branch, manually via the "Run workflow" button in the Actions tab, and on a daily schedule.
-   **`jobs`**: This section defines the jobs to be executed.
-   **`sync`**: The name of the job.
-   **`runs-on`**: The type of machine to run the job on.
-   **`environment`**: The environment to use, which gives the job access to the secrets you configured.
-   **`steps`**: The sequence of tasks to be executed.
-   **`env`**: This is where the secrets are securely passed as environment variables to the `start.py` script.

## 3. Running the Workflow

You can trigger the workflow in several ways:

*   **Scheduled:** The workflow is configured to run daily at 23:00 UTC.
*   **Manual:** You can manually trigger the workflow from the GitHub Actions UI by clicking on the "Run workflow" button.
*   **Push:** The workflow is triggered on pushes to the main branch.

## 4. Best Practices and Security

-   **Never commit secrets** to the repository.
-   **Use Environment-level secrets** for production to restrict their use to the `production` environment.
-   **Avoid printing secret values** in logs. GitHub Actions will automatically mask secrets, but it's best to avoid printing them intentionally.
-   **Rotate your secrets** if you suspect they have been leaked.

## 5. Troubleshooting

-   **Secret appears empty:**
    -   Confirm the secret exists in the `production` environment.
    -   Confirm the job is using the `production` environment.
-   **Sync is failing:**
    -   Run the script locally with the same environment variables to reproduce the issue.
    -   Check the workflow logs in the GitHub Actions tab for errors. Add debugging steps that print non-sensitive information if needed.
