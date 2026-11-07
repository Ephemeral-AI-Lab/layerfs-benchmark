set -u
cd . || exit 3
if stat -c %a . >/dev/null 2>&1; then
  mode_of() { stat -c %a "$1"; }
  size_of() { stat -c %s "$1"; }
else
  mode_of() { stat -f %Lp "$1"; }
  size_of() { stat -f %z "$1"; }
fi
if command -v sha256sum >/dev/null 2>&1; then
  hash_of() { sha256sum "$1" | cut -d' ' -f1; }
else
  hash_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
fi
find . -mindepth 1 | LC_ALL=C sort | while IFS= read -r p; do
  if [ -L "$p" ]; then
    printf 'L %s -> %s\n' "${p#.}" "$(readlink "$p")"
  elif [ -d "$p" ]; then
    printf 'D %s %s/\n' "$(mode_of "$p")" "${p#.}"
  else
    printf 'F %s %s %s %s\n' "$(mode_of "$p")" "$(size_of "$p")" "$(hash_of "$p")" "${p#.}"
  fi
done
exit 0
