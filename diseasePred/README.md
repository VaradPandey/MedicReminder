# Disease Prediction (CatBoost Hybrid)

This repository contains a disease prediction project built with CatBoost and supporting scripts.

Contents:

- `app.py`, `api_server.py` - application entry points
- Dataset files (CSV) and trained model artifacts
- `requirements.txt` - Python dependencies

Quick start (local):

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Run the app (example):

   ```powershell
   python app.py
   ```

Prepare for pushing to GitHub

1. I've created a `.gitignore` and committed project files locally. To push to GitHub you have two options:

- Option A (recommended, interactive): Use the GitHub website to create a new repository, then run the commands shown below (replace `USERNAME` and `REPO`):

  ```powershell
  git remote add origin https://github.com/USERNAME/REPO.git
  git branch -M main
  git push -u origin main
  ```

- Option B (automated): If you'd like me to create the GitHub repo for you, provide either:
  - a GitHub Personal Access Token (PAT) with `repo` scope (I'll use it only to create a repo and will not store it), and the desired repo name; or
  - a remote repository URL that I can push to (for example an existing empty repo).

What's next

- If you want, I can create the remote repo for you (requires a PAT) and push the current code.
- I can also add CI (GitHub Actions) for tests and deployment if you'd like.
