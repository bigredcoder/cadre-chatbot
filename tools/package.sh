#!/usr/bin/env bash
# Build the submission zip from a fresh clone of HEAD, with .git, never from the working folder
# (which can hold .env, .env.local, .vercel/ and .venv/). Then list the zip and fail if any
# local-only file got in.
#
#   tools/package.sh [--allow-dirty] [OUTPUT.zip]
#
# OUTPUT defaults to ../cadre-chatbot-submission.zip, next to the repo, and may not be inside it.
# Uncommitted changes are never in the zip, so it refuses to run with any unless --allow-dirty.
set -euo pipefail

# Use the first git on PATH that runs. (On the Mac this was built on, the first one is an old
# Intel-only build that bash can't start.)
GIT=""
while IFS= read -r g; do
  if "$g" --version >/dev/null 2>&1; then GIT="$g"; break; fi
done < <(type -ap git)
[ -n "$GIT" ] || { echo "No working git found on PATH." >&2; exit 1; }
git() { "$GIT" "$@"; }

REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
allow_dirty=0
out=""
for arg in "$@"; do
  case "$arg" in
    --allow-dirty) allow_dirty=1 ;;
    -*) echo "Unknown option: $arg" >&2; exit 2 ;;
    *)
      if [ -n "$out" ]; then echo "Only one output path, please." >&2; exit 2; fi
      out="$arg" ;;
  esac
done

if [ -n "$(git -C "$REPO" status --porcelain)" ]; then
  if [ "$allow_dirty" -eq 0 ]; then
    echo "Uncommitted changes. Commit them first, or pass --allow-dirty to zip HEAD anyway." >&2
    exit 1
  fi
  echo "Note: uncommitted changes are not in the zip (it holds HEAD only)."
fi

# Resolve the output to an absolute path and keep it out of the repo.
[ -n "$out" ] || out="$(dirname "$REPO")/cadre-chatbot-submission.zip"
case "$out" in /*) ;; *) out="$PWD/$out" ;; esac
out_dir="$(cd "$(dirname "$out")" && pwd -P)"
out="$out_dir/$(basename "$out")"
# -ef compares the folders themselves, so letter case and symlinks in the path don't matter.
d="$out_dir"
while :; do
  if [ "$d" -ef "$REPO" ]; then echo "The zip can't go inside the repo: $out" >&2; exit 1; fi
  if [ "$d" = / ]; then break; fi
  d="$(dirname "$d")"
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# --no-local and --single-branch copy only the commits reachable from HEAD's branch. A plain
# local clone hard-links every object, including ones no branch points to any more.
git clone --quiet --no-local --single-branch "$REPO" "$tmp/cadre-chatbot"
# Drop what points back to this machine's folder: the remote and the clone's reflog.
git -C "$tmp/cadre-chatbot" symbolic-ref --delete refs/remotes/origin/HEAD 2>/dev/null || true
git -C "$tmp/cadre-chatbot" remote remove origin
rm -rf "$tmp/cadre-chatbot/.git/logs"

# -y stores a symlink as a link, so zip can't pull in a file from outside the clone.
zip="$tmp/cadre-chatbot.zip"
(cd "$tmp" && zip -qry cadre-chatbot.zip cadre-chatbot)

# Check the zip before it leaves the temp dir. unzip -Z1 lists one entry name per line; if unzip
# fails, set -e stops here. Folder names match with or without a trailing / (a symlink has none).
names="$(unzip -Z1 "$zip")"
bad="$(printf '%s\n' "$names" \
  | grep -E '(^|/)(\.env(\.[^/]+)?|\.DS_Store)(/|$)|(^|/)(\.vercel|\.venv|node_modules|__pycache__|dist|build)(/|$)' \
  | grep -vE '(^|/)\.env\.example$' || true)"
if [ -n "$bad" ]; then
  echo "Forbidden entries in the zip (nothing written):" >&2
  echo "$bad" >&2
  exit 1
fi
mv -f "$zip" "$out"

mb="$(awk -v b="$(wc -c < "$out")" 'BEGIN { printf "%.1f", b / 1048576 }')"
entries="$(printf '%s\n' "$names" | wc -l | tr -d ' ')"
echo "Wrote $out"
echo "$mb MB, $entries entries, commit $(git -C "$REPO" rev-parse --short HEAD)."
echo "No .env, .vercel, .venv or other local-only files in it."
