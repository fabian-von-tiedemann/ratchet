d=$(mktemp -d); x=d; : ${(P)x::=/outside}; rm -rf "$d"
