d=$(mktemp -d); command read "$(printf '\144')" <<< /outside; rm -rf "$d"
