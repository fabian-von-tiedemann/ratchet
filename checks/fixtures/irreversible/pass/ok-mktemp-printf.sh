d=$(mktemp -d) && printf '%s\n' "$PWD" > "$d/x" && rm -rf "$d"
