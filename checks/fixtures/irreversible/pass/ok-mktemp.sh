d=$(mktemp -d) && echo hi > "$d/a" && cat "$d/a" && rm -rf "$d"
