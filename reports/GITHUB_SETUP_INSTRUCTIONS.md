# GitHub Metadata Setup - Step by Step

## What We're Setting

- **Description**: "Immutable memory & runtime observation scaffolding for AI consciousness"
- **Topics**: ai, llm, memory, hooks, event-sourcing, ide-integration, python

## Step 1: Generate GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name like "DivineOS Metadata"
4. Select scope: **`repo`** (full control of private repositories)
5. Click **"Generate token"**
6. **Copy the token** (you'll only see it once!)

## Step 2: Run the Setup Script

Open your terminal in the DivineOS directory and run:

```bash
python scripts/set_github_metadata.py <YOUR_TOKEN_HERE>
```

Replace `<YOUR_TOKEN_HERE>` with the token you just copied.

**Example:**
```bash
python scripts/set_github_metadata.py ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Step 3: Verify

You should see:
```
✅ Repository metadata updated successfully!
   Description: Immutable memory & runtime observation scaffolding for AI consciousness
   Topics: ai, llm, memory, hooks, event-sourcing, ide-integration, python
```

Then check GitHub:
1. Go to https://github.com/AetherLogosPrime-Architect/DivineOS
2. Scroll down to see the description and topics displayed

## Troubleshooting

**"Error: 401 Unauthorized"**
- Token is invalid or expired
- Generate a new token and try again

**"Error: 403 Forbidden"**
- Token doesn't have `repo` scope
- Generate a new token with `repo` scope selected

**"Error: 404 Not Found"**
- Repository name is incorrect
- Check the URL is correct

## Security Note

- Never commit tokens to git
- The token is only used for this one-time setup
- You can delete the token after setup from https://github.com/settings/tokens

