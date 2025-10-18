# Configuring GitHub Actions Workflow and Secrets

This document outlines the steps to configure your GitHub Actions workflow and securely manage secrets.

## 1. Adding Secrets

Secrets are used to store sensitive information such as API keys, database passwords, and other credentials. Instead of storing these values directly in your workflow file, you can store them as secrets in your GitHub repository or environment.

### Repository-Level Secrets

1.  Navigate to your repository on GitHub.
2.  Click on **Settings**.
3.  In the left sidebar, click on **Secrets and variables** then **Actions**.
4.  Click on **New repository secret**.
5.  Enter a name for your secret in the **Name** field (e.g., `LAST_FM_API`).
6.  Enter the value of your secret in the **Value** field.
7.  Click on **Add secret**.

### Environment-Level Secrets (Recommended)

Environment-level secrets provide an extra layer of protection by restricting access to secrets to specific environments.

1.  Navigate to your repository on GitHub.
2.  Click on **Settings**.
3.  In the left sidebar, click on **Environments**.
4.  Click on **New environment** or select an existing environment.
5.  Enter a name for your environment (e.g., `production`).
6.  Add environment-level secrets by clicking **Add secret**.
7.  Enter a name for your secret in the **Name** field (e.g., `LAST_FM_API`).
8.  Enter the value of your secret in the **Value** field.
9.  Click on **Add secret**.
10. You can add protection rules, e.g., required reviewers for deployments, wait timers, branch restrictions.

## 2. Referencing Secrets in Your Workflow

Once you have added your secrets, you can reference them in your workflow file using the following syntax:

```yaml
${{ secrets.SECRET_NAME }}
```

Replace `SECRET_NAME` with the name of your secret.

You can reference secrets in two ways:

### As Step Environment Variables

This is the recommended way to reference secrets.

```yaml
steps:
  - name: Run my script
    env:
      MY_SECRET: ${{ secrets.MY_SECRET }}
    run: ./my_script.sh
```

In this example, the value of the `MY_SECRET` secret will be available to the `my_script.sh` script as an environment variable.

### Directly in Commands (Not Recommended)

You can also reference secrets directly in commands, but this is not recommended because it can expose the secret in the workflow logs.

```yaml
steps:
  - name: Run my script
    run: ./my_script.sh --token "${{ secrets.MY_SECRET }}"
```

## 3. Configuring Your Workflow

Here's how to configure your workflow based on the previous discussion:

1.  **Set up the necessary secrets:**
    *   `LAST_FM_API`: Your Last.fm API key.
    *   `LAST_FM_API_SECRET`: Your Last.fm API secret.
    *   `YTMUSIC_COOKIE`: Your YouTube Music cookie.
    *   `LASTFM_SESSION`: Your Last.fm session key.
    *   `DISCORD_WEBHOOK_URL`: Your Discord webhook URL (for error notifications).
2.  **Reference these secrets** in your `[.github/workflows/sync.yml`](.github/workflows/sync.yml) file as environment variables, as shown in the previous example.
3.  **Ensure that the `environment`** in your `[.github/workflows/sync.yml`](.github/workflows/sync.yml) file matches the environment where you stored the secrets (e.g., `production`).

## 4. Running the Workflow

You can trigger the workflow in several ways:

*   **Scheduled:** The workflow is configured to run daily at 23:00 UTC.
*   **Manual:** You can manually trigger the workflow from the GitHub Actions UI by clicking on the "Run workflow" button.
*   **Push:** The workflow is triggered on pushes to the main branch.

## 5. Best Practices

*   Never commit `.env` files with secrets to the repository.
*   Use environment-level secrets for production deployments.
*   Avoid printing secret values in logs.
*   Use least privilege for tokens.
*   Use GitHub Environments protections.
*   Limit workflow triggers that have access to secrets.
*   Audit secret usage and rotate secrets if you detect leaks.