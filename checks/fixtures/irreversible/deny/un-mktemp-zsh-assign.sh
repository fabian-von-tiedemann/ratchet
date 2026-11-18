d=$(mktemp -d); echo ${d::=/outside}; rm -rf "$d"
