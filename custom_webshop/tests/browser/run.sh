#!/usr/bin/env bash
# The whole cycle: clear, build, walk, check, clear again.
#
# Every step works from the manifest the fixture builder writes, so
# nothing here can reach a record it did not create itself.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BENCH="${BENCH:-/home/frappe/frappe-bench}"
export SITE="${SITE:-erpnext}"
export OUT="${OUT:-$HERE/.run}"
export BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
mkdir -p "$OUT/shots"

# Playwright's chromium needs shared libraries a bare container often
# lacks. Point CHROME_LIBS at a directory holding them if the launch
# fails with "error while loading shared libraries".
if [ -n "${CHROME_LIBS:-}" ]; then
	export LD_LIBRARY_PATH="$CHROME_LIBS:${LD_LIBRARY_PATH:-}"
fi

py() { (cd "$BENCH/sites" && "$BENCH/env/bin/python" "$HERE/_run_in_site.py" "$SITE" "$1"); }

echo "── clearing anything left from a previous run"
py "$HERE/purge.py"

echo "── building the fixtures"
py "$HERE/fixtures.py"

# A walk that fails partway is still worth checking and must still be
# cleaned up, so neither step is allowed to abort the script.
set +e
echo "── walking them in the browser"
"$BENCH/env/bin/python" "$HERE/walk.py"
walked=$?

echo "── checking the records"
py "$HERE/verify.py"
status=$?
set -e
[ $walked -ne 0 ] && status=1

echo "── clearing up"
py "$HERE/purge.py"

exit $status
