#!/bin/bash
# Ledger for the Enzyme -> RTL migration (mitodl/hq#12637).
#
# Five metrics that erode silently during a large test migration, plus the
# mutation score. Each threshold is a floor or ceiling recorded at a known-good
# point, not an aspiration. A build that trips one of these has quietly lost
# something -- most often assertions, which no other check can see.
set -uo pipefail

FAIL=0

check() { # name actual op expected
	local name=$1 actual=$2 op=$3 expected=$4 ok
	case $op in
	ge) [[ $actual -ge $expected ]] && ok=1 || ok=0 ;;
	le) [[ $actual -le $expected ]] && ok=1 || ok=0 ;;
	*)
		echo "bad op $op"
		exit 2
		;;
	esac
	if [[ $ok -eq 1 ]]; then
		printf "  PASS  %-34s %6s  (need %s %s)\n" "$name" "$actual" "$op" "$expected"
	else
		printf "  FAIL  %-34s %6s  (need %s %s)\n" "$name" "$actual" "$op" "$expected"
		FAIL=1
	fi
}

echo "=== migration ledger ==="

# Mocha's reported count -- NOT grep -c "it(", which undercounts loop-generated
# tests by 27% and which an agent can satisfy while deleting tests.
TESTS=$(npm run test 2>&1 | grep -oE '[0-9]+ passing' | grep -oE '^[0-9]+' | tail -1)
TESTS=${TESTS:-0}
# 492 -> 505 (final review fix wave: adds the DeleteVideoDialog/
# DeleteSubtitlesDialog accept-button-wiring tests, hq#12639/hq#12640; current
# actual is 509 without a build artifact / 510 with one, so this leaves the
# +-1 build-artifact margin plus a small buffer).
check "passing tests" "$TESTS" ge 505

# May only decrease. This is the migration's actual progress metric.
# Cap was 33, not the original 31: #1564 added Dialog_test.js and Menu_test.js
# (Enzyme, for previously-untested Material components) before this ledger
# existed to gate them.
# 33 -> 28 (Tier 1, hq#12638) -> 16 (Tier 2, hq#12638). Remaining 16 =
# VideoPlayer (hq#12639) + AnalyticsChart/ProgressSlider + Tier 3's 13 files
# (hq#12640).
# 16 -> 15 (VideoPlayer extracted + converted, hq#12639).
# 15 -> 14 (Drawer_test.js converted, Tier 3 E4b/E5, hq#12640).
# 14 -> 13 (Dialog_test.js converted, Tier 3 E4b/E5, hq#12640).
# 13 -> 12 (Menu_test.js converted, Tier 3 E4b/E5, hq#12640).
# 12 -> 11 (AnalyticsChart_test.js converted, Tier 3 E4b/E5, hq#12640).
# 11 -> 10 (AnalyticsInfoTable_test.js converted, Tier 3 E4b/E5, hq#12640).
# 10 -> 9 (ProgressSlider_test.js converted, Tier 3 E4b/E5, hq#12640).
# 9 -> 8 (ToastOverlay_test.js converted, Task 3 of E4b/E5, hq#12640).
# 8 -> 7 (withPagedCollections_test.js converted, Task 3 of E4b/E5, hq#12640).
# 7 -> 6 (VideoList_test.js converted, Task 3 of E4b/E5, hq#12640).
# 6 -> 5 (DeleteVideoDialog_test.js converted, Task 4 of E4b/E5, hq#12640).
# 5 -> 4 (DeleteSubtitlesDialog_test.js converted, Task 4 of E4b/E5, hq#12640).
# 4 -> 3 (EditVideoFormDialog_test.js converted, Task 5 of E4b/E5, hq#12640).
# 3 -> 2 (VideoDetailPage_test.js converted, Task 6 of E4b/E5, hq#12640).
# 2 -> 1 (CollectionFormDialog_test.js converted, Task 7 of E4b/E5, hq#12640;
# this file held the migration's last two .state() reads).
# 1 -> 0 (CollectionDetailPage_test.js converted, Task 8 of E4b/E5, hq#12640 --
# the last Enzyme test file in the repo). The check stays here permanently as a
# le 0 regression guard: it is now what stops Enzyme coming back.
# Broadened (final review fix wave, hq#12640): the old pattern only caught
# double-quoted ES imports in *_test.js, narrower than the "Enzyme is gone"
# guarantee this check's comment claims. This also catches require() form and
# scans every .js file under static/js, not just tests. Verified to return
# zero on the current tree and to NOT match the jsdom-setup provenance
# comment at static/js/babelhook.js:22 ("adapted from
# https://airbnb.io/enzyme/docs/..."), which mentions Enzyme without
# importing it.
ENZYME=$(grep -rlE 'from .enzyme.|require\(.enzyme.\)' static/js --include='*.js' 2>/dev/null | wc -l | tr -d ' ')
check "enzyme test files" "$ENZYME" le 0

# data-testid is the escape hatch that turns an RTL migration back into
# implementation-coupled testing. 86 .find("ComponentName") selectors exist in
# the suite; without a cap the frictionless path is 86 testids, which preserves
# the exact brittleness the migration exists to remove.
#
# Counts PRODUCTION files only. A testid on an inline fixture inside a test file
# is not sprawl -- the thing worth capping is testids added to real components
# to make an RTL query easy.
TESTIDS=$(grep -rho 'data-testid' static/js --include='*.js' \
	--exclude='*_test.js' --exclude-dir=testUtils --exclude-dir=factories 2>/dev/null | wc -l | tr -d ' ')
# le 15 -> le 0 (final review fix wave, hq#12640): the migration spent none of
# its 15-testid budget end to end, so a future legitimate need should require
# a visible, reviewed ledger edit rather than quietly fitting under headroom.
check "data-testid in components" "$TESTIDS" le 0

# May only decrease.
FLOWFIX=$(grep -rho 'FlowFixMe' static/js --include='*.js' 2>/dev/null | wc -l | tr -d ' ')
# le 40 -> le 22 (final review fix wave, hq#12640): current actual is 22 after
# the full Enzyme -> RTL migration; ratchet the ceiling down to that measured
# value so it can't silently creep back up.
check "FlowFixMe occurrences" "$FLOWFIX" le 22

# Frozen. Adding a line here is how React 18 act() warnings get silenced --
# turning a real signal about un-batched state updates into future flaky tests.
# le 7 -> le 5 (Phase R1, hq#12641): the PropTypes and createClass lines
# suppressed React 15.5-era warnings that cannot fire on React 16, since both
# were removed from the react package and nothing in static/js references
# either. Leaving the cap at 7 would have left two slots of silent headroom
# in a check whose whole value is having none.
ALLOWLIST=$(grep -c 'grep -v' scripts/test/js_test.sh)
check "js_test.sh allowlist lines" "$ALLOWLIST" le 5

# The same guarantee for the other suppression surface. Capping js_test.sh at 5
# and then leaving testUtils/suppressVendorLifecycleWarnings.js uncapped would
# just relocate the erosion one file over: a seventh entry could be added with
# no threshold move, no comment discipline and no reviewer signal.
#
# Frozen at the six deprecated-lifecycle warnings React 16.9 emits for
# vendored components today (Phase R1, hq#12641):
#   2x victory 0.27.2                -> Task 7 of this PR (victory 0.27 -> 37)
#   1x rmwc 1.9.4                    -> R2, which drops rmwc entirely
#   2x react-router 4.3.1            -> no phase yet
#   1x react-document-title 2.0.3    -> no phase yet (react-side-effect 1.2.0
#                                       is unmaintained; needs a different
#                                       component, not an upgrade)
# A seventh entry is a new suppression and needs the same justification an
# allowlist line would. Task 7 must lower this to 4 when it deletes the two
# victory rows.
#
# Counts data rows only: the pattern requires leading whitespace, the
# `lifecycle:` key and a quoted value, so no prose in that file's docstring --
# which does discuss lifecycles at length -- can inflate it. Verified to
# return 6 on the current tree.
VENDORSUPP=$(grep -cE '^[[:space:]]+lifecycle: *"' \
	static/js/testUtils/suppressVendorLifecycleWarnings.js)
check "vendor lifecycle suppressions" "$VENDORSUPP" le 6

# Mutation score, when a baseline has been recorded and a report exists.
# The full run takes 30-90 minutes, so this is a per-phase or nightly check --
# the ledger reads a report, it never runs Stryker itself.
if [[ -f .stryker-baseline.json && -f reports/mutation/mutation.json ]]; then
	# Must match Stryker's own arithmetic exactly, or the computed score drifts
	# from the recorded baseline and the gate trips on nothing:
	#   - Timeout counts as DETECTED (a mutant that hangs the suite was noticed)
	#   - Ignored, CompileError and RuntimeError are excluded from the denominator
	# Verified against Stryker's reported 48.81% on the baseline run.
	SCORE=$(node -e 'const r=require("./reports/mutation/mutation.json");const skip=new Set(["Ignored","CompileError","RuntimeError"]);let k=0,t=0;for(const x of Object.values(r.files))for(const m of x.mutants){if(skip.has(m.status))continue;t++;if(m.status==="Killed"||m.status==="Timeout")k++}console.log(t?Math.round(k/t*1000)/10:0)')
	FLOOR=$(node -e 'const b=require("./.stryker-baseline.json");console.log(Math.round((b.mutationScore-b.tolerance)*10)/10)')
	if awk -v s="$SCORE" -v f="$FLOOR" 'BEGIN{exit !(s>=f)}'; then
		printf "  PASS  %-34s %6s  (floor %s)\n" "mutation score" "$SCORE" "$FLOOR"
	else
		printf "  FAIL  %-34s %6s  (floor %s)\n" "mutation score" "$SCORE" "$FLOOR"
		FAIL=1
	fi
else
	printf "  SKIP  %-34s %s\n" "mutation score" "(no baseline or report)"
fi

echo
if [[ $FAIL -ne 0 ]]; then
	echo "LEDGER FAILED -- a migration metric moved the wrong way."
	echo "If the change is intentional, update the threshold in this script in"
	echo "the same commit, and say why in the commit message."
	exit 1
fi
echo "ledger OK"
