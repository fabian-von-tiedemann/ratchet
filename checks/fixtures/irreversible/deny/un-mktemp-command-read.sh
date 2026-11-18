d=$(mktemp -d); command read d <<< /outside; rm -rf "$d"
