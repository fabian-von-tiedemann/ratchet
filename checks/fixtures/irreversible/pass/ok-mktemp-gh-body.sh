d=$(mktemp -d) && gh api repos/o/r/pulls/5 --jq .body > "$d/body.md" && gh api -X PATCH repos/o/r/pulls/5 -F body=@"$d/body.md" && rm -rf "$d"
