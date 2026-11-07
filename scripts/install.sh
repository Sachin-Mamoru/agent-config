#!/usr/bin/env bash
# Link agent-config into a workspace so Claude Code and VS Code Copilot discover it.
#
#   scripts/install.sh [--profile NAME | --all] [--dry-run] <workspace-dir>
#
# Creates (relative symlinks, so moving both folders together keeps working):
#   <ws>/.claude/skills/<skill>  -> agent-config/skills/<skill>   (one per profile entry)
#   <ws>/AGENTS.md               -> agent-config/AGENTS.md        (only if absent; Copilot/Codex)
#   <ws>/CLAUDE.md               from templates/workspace-CLAUDE.md (only if absent)
#
# Never overwrites real files or symlinks that point elsewhere. Re-run after pulling
# or after editing a profile: it refreshes links and removes links to skills that
# were dropped from the profile (only links that point into this repo).
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
profile="django-backend"
dry=0
ws=""

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) profile="${2:?--profile needs a name}"; shift 2 ;;
    --all) profile=""; shift ;;
    --dry-run) dry=1; shift ;;
    -h|--help) usage 0 ;;
    -*) echo "Unknown option: $1" >&2; usage 1 ;;
    *) ws="$1"; shift ;;
  esac
done
[ -n "$ws" ] || usage 1
[ -d "$ws" ] || { echo "Not a directory: $ws" >&2; exit 1; }
ws="$(cd "$ws" && pwd)"

relpath() { python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$2"; }
run() { if [ "$dry" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

if [ -n "$profile" ]; then
  pfile="$repo/profiles/$profile.txt"
  [ -f "$pfile" ] || { echo "No such profile: $pfile" >&2; exit 1; }
  mapfile -t skills < <(grep -vE '^\s*(#|$)' "$pfile" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
else
  mapfile -t skills < <(cd "$repo/skills" && for d in */; do [ -f "$d/SKILL.md" ] && echo "${d%/}"; done)
fi

echo "agent-config: $repo"
echo "workspace:    $ws"
echo "profile:      ${profile:-<all skills>} (${#skills[@]} skills)"

skills_dir="$ws/.claude/skills"
run mkdir -p "$skills_dir"

linked=0; skipped=0
for s in "${skills[@]}"; do
  src="$repo/skills/$s"
  [ -f "$src/SKILL.md" ] || { echo "  ! missing skill in repo: $s" >&2; exit 1; }
  dst="$skills_dir/$s"
  if [ -L "$dst" ]; then
    case "$(readlink -f "$dst")" in
      "$repo"/skills/*) run rm "$dst" ;;
      *) echo "  ~ keep $dst (symlink to somewhere else)"; skipped=$((skipped+1)); continue ;;
    esac
  elif [ -e "$dst" ]; then
    echo "  ~ keep $dst (real directory, not managed by agent-config)"; skipped=$((skipped+1)); continue
  fi
  run ln -s "$(relpath "$src" "$skills_dir")" "$dst"
  linked=$((linked+1))
done

removed=0
for l in "$skills_dir"/*; do
  [ -L "$l" ] || continue
  case "$(readlink -f "$l")" in "$repo"/skills/*) ;; *) continue ;; esac
  name="$(basename "$l")"
  printf '%s\n' "${skills[@]}" | grep -qx "$name" && continue
  run rm "$l"; echo "  - unlinked $name (not in profile)"; removed=$((removed+1))
done
echo "skills: $linked linked, $skipped kept as-is, $removed unlinked"

if [ ! -e "$ws/AGENTS.md" ]; then
  run ln -s "$(relpath "$repo/AGENTS.md" "$ws")" "$ws/AGENTS.md"
  echo "AGENTS.md: linked (read by Copilot/Codex; Claude Code reads it via CLAUDE.md import)"
else
  echo "AGENTS.md: exists, left unchanged"
fi

case "$repo/" in
  "$ws"/*) import_line="@$(relpath "$repo/AGENTS.md" "$ws")" ;;   # agent-config inside the workspace
  *)       import_line="@$repo/AGENTS.md" ;;
esac
if [ ! -e "$ws/CLAUDE.md" ]; then
  if [ "$dry" = 1 ]; then echo "  [dry-run] create $ws/CLAUDE.md from template"; else
    sed "s#@AGENT_CONFIG_AGENTS_MD#$import_line#" "$repo/templates/workspace-CLAUDE.md" > "$ws/CLAUDE.md"
  fi
  echo "CLAUDE.md: created from template — fill in the repo map"
elif ! grep -qF "$import_line" "$ws/CLAUDE.md"; then
  echo "CLAUDE.md: exists but does not import the base rules. Add this line near the top:"
  echo "  $import_line"
else
  echo "CLAUDE.md: exists and imports the base rules"
fi

echo
echo "Next: open $ws as the VS Code folder (or run 'claude' there), then type /ready."
