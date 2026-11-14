import aws_util
import book_review_util
from book_review import custom_cover_prefix
import gemini_util
import google_books_util
import os
import urllib.parse

print('Loading function')
aws = aws_util.AWSUtil()
reviews = book_review_util.BookReviewUtil()
# Unlike the utils above, these need a Parameter Store lookup to construct,
# which is real network I/O -- deferred to first use (and cached) rather
# than done at import time, so a cold Lambda import can't fail on an SSM
# call, and so tests can stub these out before anything hits AWS.
google_books = None
gemini = None


def _get_google_books():
    global google_books
    if google_books is None:
        google_books = google_books_util.GoogleBooksUtil(aws.get_parameter('GoogleBooksAPIKey'))
    return google_books


def _get_gemini():
    global gemini
    if gemini is None:
        gemini = gemini_util.GeminiUtil(aws.get_parameter('GeminiAPIKey'))
    return gemini


def _title_from_key(key):
    # Review files are named after the book's title (see sample-data/books),
    # so a delete event -- which gives us only the S3 key, not the file's
    # contents -- can still recover the 'title' partition key.
    return os.path.splitext(os.path.basename(key))[0]


# Set (to 'true') on a review's S3 object by the admin page when an edit
# should keep the book's existing cover, genres and synopsis rather than look
# them up again -- which costs a Google Books lookup and a Gemini call, and
# can come back different. S3 lowercases user metadata keys.
KEEP_DETAILS_METADATA = 'keep-book-details'


def _keep_existing_details(bucket, book_review):
    """Copies the cover/genres/synopsis already stored for this title onto
    book_review. False if there's no stored review to copy them from, in
    which case there's nothing to keep and it's looked up as usual."""
    existing = aws.get_book_review(book_review.title)
    if not existing:
        return False
    book_review.genres = list(existing.get('genres') or [])
    book_review.synopsis = existing.get('synopsis')

    # A custom cover comes from the review file itself, so only a looked-up
    # one is kept. If the file just dropped its custom cover, it goes back to
    # the one looked up before it (still stored, as nothing deletes it), or
    # if there wasn't one, looks one up (but not the rest).
    existing_cover = existing.get('cover_key')
    if book_review.cover_image or not existing_cover:
        pass
    elif not existing_cover.startswith(custom_cover_prefix(book_review.title)):
        book_review.cover_key = existing_cover
    elif aws.s3_object_exists(bucket, book_review.cover_s3_key()):
        book_review.cover_key = book_review.cover_s3_key()
    else:
        _enrich_book_review(bucket, book_review, details=False)
    return True


def _enrich_book_review(bucket, book_review, cover=True, details=True):
    """Looks the book up for its cover and/or its genres and synopsis."""
    # Cover/genre/synopsis enrichment is best-effort -- a Google Books
    # or Gemini failure (bad API key, rate limit, no match, etc.)
    # shouldn't stop the review itself from being stored. One Google
    # Books lookup serves all three, rather than a separate cover
    # provider (previously Open Library) plus a separate Books search.
    try:
        books_client = _get_google_books()
        volume_info = books_client.find_volume_info(book_review.title, book_review.author)
        if volume_info and cover:
            cover_url = books_client.find_cover_url(volume_info)
            if cover_url:
                cover_bytes = books_client.fetch_cover_image(cover_url)
                if cover_bytes:
                    cover_s3_key = book_review.cover_s3_key()
                    aws.put_s3_object(bucket, cover_s3_key, cover_bytes)
                    book_review.cover_key = cover_s3_key
                    print(f'Stored cover for "{book_review.title}" at {bucket}/{cover_s3_key}')
                else:
                    print(f'Could not download Google Books cover image for "{book_review.title}"')
            else:
                print(f'No Google Books cover found for "{book_review.title}"')

        if volume_info and details:
            book_review.genres = books_client.extract_genres(volume_info)
            description = volume_info.get('description')
            if description:
                paraphrased = _get_gemini().paraphrase_synopsis(description)
                if paraphrased:
                    book_review.synopsis = paraphrased
                    print(f'Paraphrased synopsis for "{book_review.title}"')
                else:
                    print(f'Gemini paraphrase failed for "{book_review.title}"; leaving synopsis unset')
            else:
                print(f'No Google Books description found for "{book_review.title}"')

        if not volume_info:
            print(f'No Google Books match found for "{book_review.title}"')
    except Exception as e:
        print(f'Book enrichment failed for "{book_review.title}": {e}')


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    s3_uri = f's3://{bucket}/{key}'

    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')

        # Review files are the only thing this lambda processes. This
        # notably excludes the cover images it writes into covers/ within
        # this same bucket, which would otherwise re-trigger it (and fail,
        # since a JPEG isn't valid UTF-8 markdown).
        if not key.endswith('.md'):
            print(f'Ignoring non-review S3 object: {bucket}/{key}')
            return {
                'statusCode': 200,
                'ignored': key,
            }

        if event_type.startswith('ObjectRemoved'):
            title = _title_from_key(key)
            aws.delete_book_review(title)
            aws.delete_s3_object(bucket, f'covers/{title}.jpg')
            aws.delete_s3_objects_under(bucket, custom_cover_prefix(title))
            print(f'Deleted book review "{title}" and its covers from DynamoDB/S3')
            return {
                'statusCode': 200,
                'deleted': title,
            }

        response = aws.get_s3_object(bucket, key)
        markdown_content = response['Body'].read().decode('utf-8')
        book_review = reviews.parse(markdown_content)

        if book_review.cover_image:
            book_review.cover_key = book_review.cover_image
            print(f'Using the custom cover {book_review.cover_image} for "{book_review.title}"')

        keep = response.get('Metadata', {}).get(KEEP_DETAILS_METADATA) == 'true'
        if keep and _keep_existing_details(bucket, book_review):
            print(f'Kept the existing cover/genres/synopsis for "{book_review.title}"')
        else:
            _enrich_book_review(bucket, book_review, cover=not book_review.cover_image)

        aws.store_book_review(s3_uri, book_review)
        print(f'Stored book review metadata in DynamoDB for {s3_uri}')

        # Custom covers it no longer uses: earlier uploads, or all of them if
        # it's back to a looked-up cover.
        aws.delete_s3_objects_under(bucket, custom_cover_prefix(book_review.title), keep=book_review.cover_image)

        return {
            'statusCode': 200,
            'metadata': str(book_review),
        }

    except Exception as e:
        print(f'Error processing {key} from bucket {bucket}: {str(e)}')
        raise e
