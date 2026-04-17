import os
import json
import requests

STATE_FILE = "scan_state.json"


def parse_repo(repo_url):
    parts = repo_url.replace(".git", "").split("/")
    return parts[-2], parts[-1]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_headers():
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_commit(owner, repo, branch="main"):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
    res = requests.get(url, headers=get_headers())
    res.raise_for_status()
    return res.json()["sha"]


def get_changed_files_between(owner, repo, base, head):
    url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base}...{head}"
    res = requests.get(url, headers=get_headers())
    res.raise_for_status()

    data = res.json()
    return [f["filename"] for f in data.get("files", [])]


def get_incremental_changes(repo_url, branch="main"):
    owner, repo = parse_repo(repo_url)

    state = load_state()
    repo_key = f"{owner}/{repo}"

    latest_sha = get_latest_commit(owner, repo, branch)

    if repo_key not in state:
        # First scan → full scan
        state[repo_key] = latest_sha
        save_state(state)
        return None

    last_sha = state[repo_key]

    if last_sha == latest_sha:
        return []

    changed_files = get_changed_files_between(owner, repo, last_sha, latest_sha)

    # Update state
    state[repo_key] = latest_sha
    save_state(state)

    return changed_files