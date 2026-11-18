d=$(mktemp -d) && git worktree add "$d/wt" origin/main && git -C "$d/wt" status && git worktree remove --force "$d/wt" && rm -rf "$d"
