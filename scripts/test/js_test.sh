#!/bin/bash
TMP_FILE=$(mktemp)
export TMP_FILE

if [[ -n $COVERAGE ]]; then
	export CMD="node ./node_modules/nyc/bin/nyc.js --reporter=html mocha"
elif [[ -n $CODECOV ]]; then
	export CMD="node ./node_modules/nyc/bin/nyc.js --reporter=lcovonly -R spec mocha"
elif [[ -n $WATCH ]]; then
	export CMD="node ./node_modules/mocha/bin/_mocha --watch"
else
	export CMD="node ./node_modules/mocha/bin/_mocha"
	if [[ -n $BAIL ]]; then
		export CMD="$CMD --bail"
	fi
fi

export FILE_PATTERN=${1:-'"static/**/*/*_test.js"'}
CMD_ARGS="--require ./static/js/babelhook.js static/js/global_init.js $FILE_PATTERN"

# Second argument (if specified) should be a string that will match specific test case descriptions
#
# EXAMPLE:
#   (./static/js/SomeComponent_test.js)
#   it('should test basic arithmetic') {
#     assert.equal(1 + 1, 2);
#   }
#
#   (in command line...)
#   > ./js_test.sh static/js/SomeComponent_test.js "should test basic arithmetic"
if [[ -n $2 ]]; then
	CMD_ARGS+=" -g \"$2\""
fi

echo "Running: $CMD $CMD_ARGS"

eval "$CMD $CMD_ARGS" 2> >(tee "$TMP_FILE")

export TEST_RESULT=$?

if [[ $TEST_RESULT -ne 0 ]]; then
	echo "Tests failed, exiting with error $TEST_RESULT..."
	rm -f "$TMP_FILE"
	exit 1
fi

if [[ $(
	cat "$TMP_FILE" |
		grep -v 'ignored, nothing could be mapped' |
		grep -v "This browser doesn't support the \`onScroll\` event" |
		grep -v "Warning: Accessing PropTypes via the main React package is deprecated" |
		grep -v "Warning: Accessing createClass via the main React package is deprecated" |
		grep -v 'VIDEOJS: WARN: A plugin named "qualityLevels" already exists' |
		grep -v "\[react-ga\] ReactGA.initialize must be called first" |
		wc -l |
		awk '{print $1}'
) -ne 0 ]]; then # is file empty?
	echo "Error output found:"
	cat "$TMP_FILE"
	echo "End of output"
	rm -f "$TMP_FILE"
	exit 1
fi

rm -f "$TMP_FILE"
