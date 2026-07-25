# Book rating elements are scored 0-10 (see RatingChart.js's MAX_RATING).
# This maps that weighted 0-10 score onto a 0-5 star display using a
# non-linear step scale: whole stars up through 2, half-star granularity
# from 2-4 stars, and quarter-star granularity only in the 4-5 star range.
# Each entry is the 0-10 score at which that star value begins.
STAR_RATING_THRESHOLDS = [
    (0, 0.0),
    (1.1, 1.0),
    (2.2, 2.0),
    (4.5, 3.0),
    (5.25, 3.5),
    (7, 4.0),
    (7.5, 4.25),
    (8, 4.5),
    (8.5, 4.75),
    (9, 5.0),
]


def weighted_rating(rating_elements):
    """Overall 0-10 rating for a book: the weighted average of its rating
    elements. Returns None if there's nothing to weight."""
    total_weight = sum(el['weight'] for el in rating_elements)
    if not total_weight:
        return None
    return sum(el['rating'] * el['weight'] for el in rating_elements) / total_weight


def rating_to_stars(rating):
    """Convert a 0-10 rating into a 0-5 star rating via STAR_RATING_THRESHOLDS."""
    stars = STAR_RATING_THRESHOLDS[0][1]
    for threshold, value in STAR_RATING_THRESHOLDS:
        if rating < threshold:
            break
        stars = value
    return stars


def add_star_rating(book):
    """Annotate a book dict with 'star_rating' (0-5, or None if it has no
    rating elements), derived from its weighted 0-10 rating elements."""
    rating = weighted_rating(book.get('rating_elements') or [])
    book['star_rating'] = rating_to_stars(rating) if rating is not None else None
    return book
