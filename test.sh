echo "Starting firebase emulator"
firebase emulators:start > /dev/stdout &
LOGS_PID=$!
sleep 10

echo "running tests"
cd test
mocha loginUrl.js --timeout 99999999999 --bail --reporter spec || TEST_FAILED=true
# Prompt for environment variables
read -p "Enter COUNTRY_CODE: " COUNTRY_CODE
read -p "Enter CODE_VERIFIER: " CODE_VERIFIER
read -p "Enter SERIAL: " SERIAL
# Prompt the user to save the response_url
read -p "Please save the response_url to test/response_url.txt, then press Enter to continue."

# Optionally, you can add a check to ensure the file is not empty
if [ ! -s "response_url.txt" ]; then
    echo "Warning: response_url.txt is empty. Please make sure you've saved the URL correctly."
fi


# Export the variables
export COUNTRY_CODE
export CODE_VERIFIER
export SERIAL

# Run the second test file
mocha auth.js --timeout 99999999999 --bail --reporter spec || TEST_FAILED=true

# Run the second test file
mocha storage.js --timeout 99999999999 --bail --reporter spec || TEST_FAILED=true


# Stop the logs stream
kill $LOGS_PID

# Exit with error if tests failed
if [ "$TEST_FAILED" = true ]; then
    exit 1
fi
sleep 5