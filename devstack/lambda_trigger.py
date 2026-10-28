"""
Stands in for S3 invoking the content Lambdas (terraform/content_lambdas.tf).
devstack/seed.py points the content buckets' event notifications at a queue,
and this runs each event's bucket's Lambda on it, with the same event S3
would invoke it with.

Each invocation is its own process, from the source mounted at /repo, so an
edit takes effect on the next event without a restart.
"""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REPO = Path(__file__).resolve().parent.parent
INVOKE_SCRIPT = Path(__file__).resolve().parent / 'invoke_lambda.py'

FUNCTIONS = {
    'spark.wiki.blog': 'UpdateBlogPostMetadata',
    'spark.wiki.books': 'UpdateBookReview',
    'spark.wiki.photos': 'UpdatePhotoMetadata',
}
EVENTS_QUEUE = 'content-events'
CONCURRENCY = 4
# The longest any of the Lambdas is allowed (UpdateBookReview's), and then some.
TIMEOUT_SECONDS = 600

sqs = boto3.client('sqs')


def log(message):
    print(message, flush=True)


def wait_for_queue():
    """The queue's URL, once seed has made it -- again, if the emulator
    restarts."""
    while True:
        try:
            return sqs.get_queue_url(QueueName=EVENTS_QUEUE)['QueueUrl']
        except (BotoCoreError, ClientError):
            time.sleep(2)


def invoke(function, event):
    """Runs the Lambda on the event, returning whether it succeeded, and its
    output -- kept together, rather than interleaved with whatever else is
    running at the time, as each invocation's is in CloudWatch."""
    try:
        process = subprocess.run(
            [f'/lambdas/{function}/bin/python', str(INVOKE_SCRIPT), str(REPO / 'ContentManagement' / function / 'src')],
            input=json.dumps(event),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        return process.returncode == 0, process.stdout
    except subprocess.TimeoutExpired as e:
        # What it printed before then, which can be bytes even in text mode.
        output = e.output.decode(errors='replace') if isinstance(e.output, bytes) else e.output or ''
        return False, f'{output}Timed out after {TIMEOUT_SECONDS}s\n'


def handle(queue_url, message):
    event = json.loads(message['Body'])
    # Every event from S3 has exactly one record. What doesn't is the test
    # event S3 sends when notifications are first set up.
    records = event.get('Records')
    if records:
        record = records[0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        function = FUNCTIONS.get(bucket)
        if function:
            succeeded, output = invoke(function, event)
            outcome = 'succeeded' if succeeded else 'FAILED'
            lines = [f'{function} {outcome} on {record["eventName"]} s3://{bucket}/{key}']
            lines += [f'  {line}' for line in output.splitlines()]
            log('\n'.join(lines))
        else:
            log(f'No Lambda for s3://{bucket}/{key}')
    # As a failed asynchronous invocation eventually is, rather than retried
    # until it's fixed.
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])


def main():
    queue_url = wait_for_queue()
    log(f'Running {", ".join(sorted(set(FUNCTIONS.values())))} on events from {EVENTS_QUEUE}')
    with ThreadPoolExecutor(CONCURRENCY) as pool:
        while True:
            try:
                messages = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=CONCURRENCY,
                    WaitTimeSeconds=10,
                ).get('Messages', [])
                # Each batch finishes before the next, so no more than
                # CONCURRENCY run at once.
                for result in [pool.submit(handle, queue_url, m) for m in messages]:
                    result.result()
            except (BotoCoreError, ClientError) as e:
                log(f'Lost the queue ({e}), waiting for it')
                queue_url = wait_for_queue()


if __name__ == '__main__':
    sys.exit(main())
