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
check "passing tests" "$TESTS" ge 492

# May only decrease. This is the migration's actual progress metric.
# Cap was 33, not the original 31: #1564 added Dialog_test.js and Menu_test.js
# (Enzyme, for previously-untested Material components) before this ledger
# existed to gate them.
# 33 -> 28 (Tier 1, hq#12638) -> 16 (Tier 2, hq#12638). Remaining 16 =
# VideoPlayer (hq#12639) + AnalyticsChart/ProgressSlider + Tier 3's 13 files
# (hq#12640).
# 16 -> 15 (VideoPlayer extracted + converted, hq#12639).
ENZYME=$(grep -rl 'from "enzyme"' static/js --include='*_test.js' 2>/dev/null | wc -l | tr -d ' ')
check "enzyme test files" "$ENZYME" le 15

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
check "data-testid in components" "$TESTIDS" le 15

# May only decrease.
FLOWFIX=$(grep -rho 'FlowFixMe' static/js --include='*.js' 2>/dev/null | wc -l | tr -d ' ')
check "FlowFixMe occurrences" "$FLOWFIX" le 40

# Frozen. Adding a line here is how React 18 act() warnings get silenced --
# turning a real signal about un-batched state updates into future flaky tests.
ALLOWLIST=$(grep -c 'grep -v' scripts/test/js_test.sh)
check "js_test.sh allowlist lines" "$ALLOWLIST" le 7

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
