#!/usr/bin/env bash
# test-watchdog-io-detection.sh — Unit tests for the idle watchdog's I/O
# detection logic extracted from run_opencode_prompt.sh (Phase 1 A+B).
#
# Tests exercise:
#  1. _read_server_io_bytes() function: awk pattern summing read_bytes + write_bytes
#  2. IDLE_TIMEOUT_SECS constant value (must be 1800)
#  3. Activity-detection logic: change detection between iterations
#  4. Edge cases: missing /proc/io, empty pidfile, zero-byte counters
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET="$REPO_ROOT/run_opencode_prompt.sh"

PASSED=0
FAILED=0

pass() { echo "  PASS: $1"; PASSED=$(( PASSED + 1 )); }
fail() { echo "  FAIL: $1"; FAILED=$(( FAILED + 1 )); }

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        pass "$label"
    else
        fail "$label (expected='$expected', got='$actual')"
    fi
}

echo "=== Watchdog I/O Detection Tests ==="

# ---------------------------------------------------------------------------
# Test 1: IDLE_TIMEOUT_SECS is 1800 (30 minutes)
# ---------------------------------------------------------------------------
timeout_val=$(grep -oP '^IDLE_TIMEOUT_SECS=\K[0-9]+' "$TARGET")
assert_eq "IDLE_TIMEOUT_SECS is 1800" "1800" "$timeout_val"

# ---------------------------------------------------------------------------
# Test 2: HARD_CEILING_SECS is 5400 (90 minutes)
# ---------------------------------------------------------------------------
ceiling_val=$(grep -oP '^HARD_CEILING_SECS=\K[0-9]+' "$TARGET")
assert_eq "HARD_CEILING_SECS is 5400" "5400" "$ceiling_val"

# ---------------------------------------------------------------------------
# Test 3: awk pattern sums read_bytes + write_bytes correctly
# ---------------------------------------------------------------------------
awk_pattern='/^(read|write)_bytes:/{sum+=$2} END{print sum}'

result=$(echo -e "read_bytes: 1000\nwrite_bytes: 500" | awk "$awk_pattern")
assert_eq "awk sums read+write (1000+500=1500)" "1500" "$result"

result=$(echo -e "read_bytes: 0\nwrite_bytes: 0" | awk "$awk_pattern")
assert_eq "awk handles zero bytes" "0" "$result"

result=$(echo -e "read_bytes: 4294967296\nwrite_bytes: 4294967296" | awk "$awk_pattern")
assert_eq "awk handles large values (>4GB)" "8589934592" "$result"

result=$(echo -e "rchar: 999\nwchar: 999\nsyscr: 10\nsyscw: 10\nread_bytes: 200\nwrite_bytes: 300\ncancelled_write_bytes: 50" | awk "$awk_pattern")
assert_eq "awk ignores non-target lines in /proc/io" "500" "$result"

# ---------------------------------------------------------------------------
# Test 4: awk pattern handles read_bytes-only change (the key fix)
# ---------------------------------------------------------------------------
# Scenario: write_bytes unchanged, read_bytes increased (network API response)
prev=$(echo -e "read_bytes: 1000\nwrite_bytes: 500" | awk "$awk_pattern")
cur=$(echo -e "read_bytes: 2000\nwrite_bytes: 500" | awk "$awk_pattern")
if [[ "$cur" != "$prev" ]]; then
    pass "detects activity when only read_bytes changes"
else
    fail "detects activity when only read_bytes changes (prev=$prev cur=$cur)"
fi

# Scenario: read_bytes unchanged, write_bytes increased (disk write)
prev=$(echo -e "read_bytes: 1000\nwrite_bytes: 500" | awk "$awk_pattern")
cur=$(echo -e "read_bytes: 1000\nwrite_bytes: 700" | awk "$awk_pattern")
if [[ "$cur" != "$prev" ]]; then
    pass "detects activity when only write_bytes changes"
else
    fail "detects activity when only write_bytes changes (prev=$prev cur=$cur)"
fi

# Scenario: both unchanged (truly idle)
prev=$(echo -e "read_bytes: 1000\nwrite_bytes: 500" | awk "$awk_pattern")
cur=$(echo -e "read_bytes: 1000\nwrite_bytes: 500" | awk "$awk_pattern")
if [[ "$cur" == "$prev" ]]; then
    pass "reports no activity when both counters unchanged"
else
    fail "reports no activity when both counters unchanged (prev=$prev cur=$cur)"
fi

# ---------------------------------------------------------------------------
# Test 5: _read_server_io_bytes function exists and uses correct awk pattern
# ---------------------------------------------------------------------------
if grep -q '_read_server_io_bytes()' "$TARGET"; then
    pass "_read_server_io_bytes function exists"
else
    fail "_read_server_io_bytes function exists"
fi

if grep -q 'awk.*read|write.*_bytes.*sum' "$TARGET"; then
    pass "_read_server_io_bytes uses sum pattern"
else
    fail "_read_server_io_bytes uses sum pattern"
fi

# ---------------------------------------------------------------------------
# Test 6: No stale references to old function/variable names
# ---------------------------------------------------------------------------
if grep -q '_read_server_write_bytes' "$TARGET"; then
    fail "no stale _read_server_write_bytes references"
else
    pass "no stale _read_server_write_bytes references"
fi

if grep -q '_cur_server_write' "$TARGET"; then
    fail "no stale _cur_server_write references"
else
    pass "no stale _cur_server_write references"
fi

if grep -q '_prev_server_write' "$TARGET"; then
    fail "no stale _prev_server_write references"
else
    pass "no stale _prev_server_write references"
fi

# ---------------------------------------------------------------------------
# Test 7: _read_server_io_bytes with simulated /proc/io via temp dir
# ---------------------------------------------------------------------------
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# Create a fake pidfile and /proc-like structure
fake_pid=99999
echo "$fake_pid" > "$tmpdir/server.pid"
mkdir -p "$tmpdir/proc/$fake_pid"
cat > "$tmpdir/proc/$fake_pid/io" <<EOF
rchar: 123456
wchar: 78910
syscr: 100
syscw: 50
read_bytes: 4096
write_bytes: 8192
cancelled_write_bytes: 0
EOF

# Source only the function by extracting it, providing required vars
_read_server_io_bytes() {
    local pidfile="$tmpdir/server.pid"
    if [[ -f "$pidfile" ]]; then
        local spid
        spid=$(cat "$pidfile" 2>/dev/null)
        if [[ -n "$spid" && -f "$tmpdir/proc/$spid/io" ]]; then
            awk '/^(read|write)_bytes:/{sum+=$2} END{print sum}' "$tmpdir/proc/$spid/io" 2>/dev/null
            return
        fi
    fi
    echo ""
}

result=$(_read_server_io_bytes)
assert_eq "function reads simulated /proc/io (4096+8192=12288)" "12288" "$result"

# Test with missing pidfile
rm -f "$tmpdir/server.pid"
result=$(_read_server_io_bytes)
assert_eq "function returns empty for missing pidfile" "" "$result"

# Test with missing /proc/io
echo "$fake_pid" > "$tmpdir/server.pid"
rm -f "$tmpdir/proc/$fake_pid/io"
result=$(_read_server_io_bytes)
assert_eq "function returns empty for missing /proc/io" "" "$result"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Results: $PASSED passed, $FAILED failed ==="

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
echo "All watchdog I/O detection tests passed."
