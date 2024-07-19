echo "Starting firebase emulator"
firebase emulators:start > /dev/stdout &
LOGS_PID=$!
sleep 10

echo "running tests"
cd test
mocha test.js --timeout 99999999999 --bail --reporter spec || TEST_FAILED=true

# Stop the logs stream
kill $LOGS_PID

# Exit with error if tests failed
if [ "$TEST_FAILED" = true ]; then
    exit 1
fi
sleep 10