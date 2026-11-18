d=$(mktemp -d); time read d <<< /outside; rm -rf "$d"
