tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT; echo hi > "$tmp/x"
