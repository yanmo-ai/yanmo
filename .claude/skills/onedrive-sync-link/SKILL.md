---
name: onedrive-sync-link
description: Validate provided Windows/Mac OneDrive links, update download buttons, commit, and push.
argument-hint: "[target-file] [commit-message] [windows-url] [mac-url]"
user-invocable: true
---

# OneDrive link validate + update + push

Use this skill when user provides direct Windows and Mac OneDrive links.

## Required login context

- Sign in with `huanchen@microsoft.com` using Azure CLI:
  - `az login --allow-no-subscriptions`
- Use SharePoint access token from current Azure CLI session:
  - `az account get-access-token --resource https://microsoftapc-my.sharepoint.com`

## Arguments

- `$1` = target file (optional, default `index.html`)
- `$2` = commit message (optional, default `chore: update OneDrive download links`)
- `$3` = Windows URL (required)
- `$4` = Mac URL (required)

## Behavior

1. Validate login user is `huanchen@microsoft.com`.
2. Require both Windows and Mac URLs.
3. Append or overwrite `download=1` for both URLs.
4. Validate host is `microsoftapc-my.sharepoint.com`.
5. Validate both links are downloadable via authenticated `curl` using SharePoint bearer token.
6. Update HTML anchors by labels:
   - `下载 Windows 版`
   - `下载 Mac 版`
7. Commit only if target file changed.
8. Push to remote automatically if commit succeeds.

## Commands

```bash
TARGET_FILE="${1:-index.html}"
COMMIT_MSG="${2:-chore: update OneDrive download links}"
WIN_URL_INPUT="${3:-}"
MAC_URL_INPUT="${4:-}"
WIN_LABEL="下载 Windows 版"
MAC_LABEL="下载 Mac 版"

if [ -z "$WIN_URL_INPUT" ] || [ -z "$MAC_URL_INPUT" ]; then
  echo "Usage: /onedrive-sync-link [target-file] [commit-message] <windows-url> <mac-url>" >&2
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI is required. Install 'az' first." >&2
  exit 1
fi

ACTIVE_USER=$(az account show --query user.name -o tsv 2>/dev/null)
if [ "$ACTIVE_USER" != "huanchen@microsoft.com" ]; then
  echo "Please login with huanchen@microsoft.com first: az login --allow-no-subscriptions" >&2
  exit 1
fi

SP_TOKEN=$(az account get-access-token --resource https://microsoftapc-my.sharepoint.com --query accessToken -o tsv | tr -d '\r\n')
if [ -z "$SP_TOKEN" ]; then
  echo "Failed to get SharePoint token from Azure CLI session." >&2
  exit 1
fi

normalize_url() {
  python - "$1" <<'PY'
import sys
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
u=sys.argv[1]
p=urlparse(u)
q=dict(parse_qsl(p.query, keep_blank_values=True))
q['download']='1'
print(urlunparse((p.scheme,p.netloc,p.path,p.params,urlencode(q),p.fragment)))
PY
}

validate_host() {
  python - "$1" <<'PY'
import sys
from urllib.parse import urlparse
u=sys.argv[1]
p=urlparse(u)
if p.netloc.lower() != 'microsoftapc-my.sharepoint.com':
    raise SystemExit('Unexpected share host: ' + p.netloc)
PY
}

validate_downloadable() {
  URL="$1"
  KIND="$2"
  TMP_FILE=$(mktemp /tmp/onedrive_probe.XXXXXX)
  if ! curl.exe -sS -L -f -H "Authorization: Bearer ${SP_TOKEN}" "$URL" -o "$TMP_FILE"; then
    rm -f "$TMP_FILE"
    echo "${KIND} link is not downloadable with authenticated curl.exe." >&2
    exit 1
  fi
  if [ ! -s "$TMP_FILE" ]; then
    rm -f "$TMP_FILE"
    echo "${KIND} link download probe returned empty content." >&2
    exit 1
  fi
  rm -f "$TMP_FILE"
}

WIN_URL=$(normalize_url "$WIN_URL_INPUT")
MAC_URL=$(normalize_url "$MAC_URL_INPUT")

validate_host "$WIN_URL"
validate_host "$MAC_URL"

validate_downloadable "$WIN_URL" "Windows"
validate_downloadable "$MAC_URL" "Mac"

python .claude/skills/onedrive-sync-link/scripts/update_download_link.py --file "$TARGET_FILE" --label "$WIN_LABEL" --url "$WIN_URL"
python .claude/skills/onedrive-sync-link/scripts/update_download_link.py --file "$TARGET_FILE" --label "$MAC_LABEL" --url "$MAC_URL"

if git diff --quiet -- "$TARGET_FILE"; then
  echo "No link changes detected; skip commit and push."
  exit 0
fi

git diff -- "$TARGET_FILE"
git add "$TARGET_FILE"
git commit -m "$COMMIT_MSG"
git push
```
