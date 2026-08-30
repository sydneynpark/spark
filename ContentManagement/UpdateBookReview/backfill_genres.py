"""One-off backfill: re-derive `genres` on every existing spark.wiki.books
DynamoDB item using GoogleBooksUtil.extract_genres (see src/google_books_util.py),
without any new Google Books/Gemini API calls.

Existing items already have the pre-cleanup raw BISAC category paths sitting
in `genres` -- that's literally what the lambda used to write there before
extract_genres existed -- so this treats each item's current `genres` list
as the input `categories`, runs it through the same cleanup the lambda now
does for new reviews, and overwrites just the `genres` attribute. cover_key,
synopsis, and everything else on the item is left untouched.

Run locally against real AWS credentials for the account/region that holds
the table (this does not use LocalAWSUtil/sample-data -- there's nothing to
back-fill in the local sample data, only in the real table):

    python backfill_genres.py --dry-run   # preview changes, writes nothing
    python backfill_genres.py             # apply
"""
import argparse
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from google_books_util import GoogleBooksUtil

TABLE_NAME = 'spark.wiki.books'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Print planned changes without writing them')
    args = parser.parse_args()

    table = boto3.resource('dynamodb').Table(TABLE_NAME)
    # extract_genres is pure logic over a dict -- no API key needed.
    extractor = GoogleBooksUtil(api_key=None)

    updated = 0
    unchanged = 0
    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get('Items', []):
            old_genres = item.get('genres', [])
            if not old_genres:
                continue

            new_genres = extractor.extract_genres({'categories': old_genres})
            if new_genres == old_genres:
                unchanged += 1
                continue

            title, date = item['title'], item['date']
            print(f'{title} ({date}):')
            print(f'  old: {old_genres}')
            print(f'  new: {new_genres}')
            if not args.dry_run:
                table.update_item(
                    Key={'title': title, 'date': date},
                    UpdateExpression='SET genres = :g',
                    ExpressionAttributeValues={':g': new_genres},
                )
            updated += 1

        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    verb = 'Would update' if args.dry_run else 'Updated'
    print(f'\n{verb} {updated} item(s); {unchanged} already clean.')


if __name__ == '__main__':
    main()
