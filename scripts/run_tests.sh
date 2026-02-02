#!/bin/bash
set -e

./scripts/setup_test_db.sh

export TEST_DATABASE_URL="postgresql://iot:iot_dev@localhost:5432/iotcloud_test"

if [ "$1" == "unit" ]; then
    pytest -m unit "$@"
elif [ "$1" == "integration" ]; then
    pytest -m integration "$@"
elif [ "$1" == "e2e" ]; then
    pytest -m e2e "$@"
elif [ "$1" == "all" ]; then
    pytest "$@"
else
    pytest "$@"
fi
