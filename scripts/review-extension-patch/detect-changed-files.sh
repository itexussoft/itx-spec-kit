#!/usr/bin/env bash
# Patch for spec-kit-review changed-files detection:
# include untracked files in addition to tracked diffs.

set -e

JSON_MODE=false

for arg in "$@"; do
 case "$arg" in
 --json) JSON_MODE=true ;;
 --help|-h)
 cat << 'EOF'
Usage: detect-changed-files.sh [OPTIONS]

Detect changed files for code review.

Includes tracked changes (committed/staged/unstaged) and untracked files.

OPTIONS:
 --json Output in JSON format
 --help, -h Show this help message
EOF
 exit 0
 ;;
 *) echo "ERROR: Unknown option '$arg'" >&2; exit 1 ;;
 esac
done

json_escape() {
 local s="$1"
 s="${s//\\/\\\\}"
 s="${s//\"/\\\"}"
 s="${s//$'\t'/\\t}"
 s="${s//$'\n'/\\n}"
 s="${s//$'\r'/\\r}"
 printf '%s' "$s"
}

fmt_array() {
 local arr=("$@")
 if [[ ${#arr[@]} -eq 0 ]]; then echo "[]"; return; fi
 local first=true
 local result="["
 for item in "${arr[@]}"; do
 if $first; then first=false; else result+=","; fi
 result+="\"$(json_escape "$item")\""
 done
 result+="]"
 echo "$result"
}

error_exit() {
 local message="$1"
 local code="${2:-1}"
 if $JSON_MODE; then
 printf '{"error":"%s"}\n' "$(json_escape "$message")"
 else
 echo "Error: $message" >&2
 fi
 exit "$code"
}

collect_z_paths() {
 local cmd=("$@")
 local out=()
 while IFS= read -r -d '' line; do
 [[ -n "$line" ]] && out+=("$line")
 done < <("${cmd[@]}" 2>/dev/null)
 printf '%s\0' "${out[@]}"
}

append_unique() {
 local candidate="$1"
 [[ -z "$candidate" ]] && return 0
 for existing in "${CHANGED_FILES[@]}"; do
 if [[ "$existing" == "$candidate" ]]; then
 return 0
 fi
 done
 CHANGED_FILES+=("$candidate")
}

if ! command -v git >/dev/null 2>&1; then
 error_exit "git is not available. The review extension requires git to identify changed files." 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
 error_exit "Not a git repository. The review extension requires git to identify changed files." 1
fi

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
DEFAULT_BRANCH=""

symref=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null || echo "")
if [[ -n "$symref" ]]; then
 DEFAULT_BRANCH="${symref##refs/remotes/origin/}"
fi
if [[ -z "$DEFAULT_BRANCH" ]] && git rev-parse --verify origin/main >/dev/null 2>&1; then
 DEFAULT_BRANCH="main"
fi
if [[ -z "$DEFAULT_BRANCH" ]] && git rev-parse --verify origin/master >/dev/null 2>&1; then
 DEFAULT_BRANCH="master"
fi

CHANGED_FILES=()
MODE=""

if [[ -n "$CURRENT_BRANCH" && -n "$DEFAULT_BRANCH" && "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" ]]; then
 MERGE_BASE=$(git merge-base "origin/$DEFAULT_BRANCH" HEAD 2>/dev/null || echo "")
 if [[ -n "$MERGE_BASE" ]]; then
 COMMITTED=()
 while IFS= read -r -d '' line; do COMMITTED+=("$line"); done < <(git diff --name-only -z --diff-filter=ACMR "${MERGE_BASE}...HEAD" 2>/dev/null)
 STAGED=()
 while IFS= read -r -d '' line; do STAGED+=("$line"); done < <(git diff --cached --name-only -z --diff-filter=ACMR 2>/dev/null)
 UNSTAGED=()
 while IFS= read -r -d '' line; do UNSTAGED+=("$line"); done < <(git diff --name-only -z --diff-filter=ACMR 2>/dev/null)
 UNTRACKED=()
 while IFS= read -r -d '' line; do UNTRACKED+=("$line"); done < <(git ls-files --others --exclude-standard -z 2>/dev/null)

 for f in "${COMMITTED[@]}" "${STAGED[@]}" "${UNSTAGED[@]}" "${UNTRACKED[@]}"; do
 append_unique "$f"
 done
 MODE="Feature branch diff (${DEFAULT_BRANCH}...HEAD) + uncommitted + untracked changes"
 else
 DEFAULT_BRANCH=""
 fi
fi

if [[ -z "$MODE" ]]; then
 STAGED=()
 while IFS= read -r -d '' line; do STAGED+=("$line"); done < <(git diff --cached --name-only -z --diff-filter=ACMR 2>/dev/null)
 UNSTAGED=()
 while IFS= read -r -d '' line; do UNSTAGED+=("$line"); done < <(git diff --name-only -z --diff-filter=ACMR 2>/dev/null)
 UNTRACKED=()
 while IFS= read -r -d '' line; do UNTRACKED+=("$line"); done < <(git ls-files --others --exclude-standard -z 2>/dev/null)

 for f in "${STAGED[@]}" "${UNSTAGED[@]}" "${UNTRACKED[@]}"; do
 append_unique "$f"
 done
 MODE="Working directory changes (staged + unstaged + untracked)"
 [[ -z "$DEFAULT_BRANCH" ]] && DEFAULT_BRANCH="(unknown)"
fi

if [[ ${#CHANGED_FILES[@]} -eq 0 ]]; then
 if $JSON_MODE; then
 printf '{"branch":"%s","default_branch":"%s","mode":"%s","changed_files":[],"message":"No changes detected. Nothing to review."}\n' \
 "$(json_escape "$CURRENT_BRANCH")" "$(json_escape "$DEFAULT_BRANCH")" "$(json_escape "$MODE")"
 else
 echo "No changes detected. Nothing to review."
 fi
 exit 2
fi

if $JSON_MODE; then
 printf '{"branch":"%s","default_branch":"%s","mode":"%s","changed_files":%s}\n' \
 "$(json_escape "$CURRENT_BRANCH")" "$(json_escape "$DEFAULT_BRANCH")" "$(json_escape "$MODE")" "$(fmt_array "${CHANGED_FILES[@]}")"
else
 echo "BRANCH: $CURRENT_BRANCH"
 echo "DEFAULT_BRANCH: $DEFAULT_BRANCH"
 echo "MODE: $MODE"
 echo "CHANGED_FILES:"
 for f in "${CHANGED_FILES[@]}"; do
 echo " $f"
 done
fi

exit 0
