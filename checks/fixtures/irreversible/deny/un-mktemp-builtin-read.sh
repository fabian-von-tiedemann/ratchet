d=$(mktemp -d); builtin read d <<< /outside; rm -rf "$d"
