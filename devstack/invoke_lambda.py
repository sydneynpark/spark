"""
Runs a Lambda's handler on one event, as Lambda would invoke it:

    python invoke_lambda.py <the Lambda's src directory> < event.json

devstack/lambda_trigger.py runs this with the Lambda's own virtualenv.
"""

import json
import sys
import time

sys.path.insert(0, sys.argv[1])
event = json.load(sys.stdin)

import lambda_function  # noqa: E402

start = time.monotonic()
result = lambda_function.lambda_handler(event, None)
print(f'Returned {result!r} in {time.monotonic() - start:.1f}s')
