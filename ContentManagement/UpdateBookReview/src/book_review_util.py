import frontmatter
from book_review import BookReview


class BookReviewUtil:
    def __init__(self):
        pass

    def parse(self, markdown_content):
        post = frontmatter.loads(markdown_content)

        book_review = BookReview(post)
        book_review.debug_print()

        return book_review
