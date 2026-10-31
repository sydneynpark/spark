import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.draft_util import (  # noqa: E402
    DraftError, build_markdown, draft_fields, draft_id_from_key, draft_photo, draft_photo_key,
    parse_draft, plan_publish,
)
from utils.photo_upload_util import UploadPathError  # noqa: E402
from utils.post_util import frontmatter_tags, parse_post  # noqa: E402

DRAFT_ID = '0123456789abcdef0123456789abcdef'
PREFIX = f'drafts/{DRAFT_ID}/'


def fields(**overrides):
    return {
        'title': 'Marsh Morning',
        'date': '2026-10-28',
        'written': '',
        'tags': [],
        'preview': '',
        'photo': '',
        'content': '',
        **overrides,
    }


class TestDraftFields(unittest.TestCase):

    def test_a_draft_can_be_saved_before_it_has_a_title_or_date(self):
        self.assertEqual(draft_fields({}), fields(title='', date=''))

    def test_a_written_date_is_optional(self):
        self.assertEqual(draft_fields({'date': '2019-07-28', 'written': ' 2026-10-30'})['written'], '2026-10-30')
        self.assertEqual(draft_fields({'date': '2019-07-28'})['written'], '')

    def test_strips_everything_but_the_body(self):
        result = draft_fields({'title': '  Hi ', 'date': ' 2026-10-28', 'content': '  indented\n'})
        self.assertEqual(result['title'], 'Hi')
        self.assertEqual(result['date'], '2026-10-28')
        self.assertEqual(result['content'], '  indented\n')

    def test_rejects_a_date_that_isnt_one(self):
        for date in ('2026-02-30', '10/28/2026', 'soon'):
            with self.assertRaises(DraftError):
                draft_fields({'date': date})
            with self.assertRaises(DraftError):
                draft_fields({'date': '2026-10-28', 'written': date})

    def test_tags(self):
        self.assertEqual(draft_fields({'tags': [' Road  Trip ', 'Colorado', 'road trip', '']})['tags'], ['Road Trip', 'Colorado'])
        with self.assertRaises(DraftError):
            draft_fields({'tags': ['x' * 51]})

    def test_rejects_a_thumbnail_that_isnt_a_photo_reference(self):
        with self.assertRaises(DraftError):
            draft_fields({'photo': 'https://example.com/a.jpg'})


class TestMarkdown(unittest.TestCase):

    def test_round_trips_through_the_post_format(self):
        draft = fields(
            title='Marsh Morning: Day 2',
            written='2026-10-30',
            tags=['Road Trip', 'Colorado: Day 2'],
            preview='Grebes, "egrets", and more',
            photo=f'photo://{PREFIX}birds/a b.jpg',
            content=f'# Hi\n\n`photo://{PREFIX}birds/a b.jpg`',
        )
        self.assertEqual(parse_draft(build_markdown(draft)), draft)

    def test_leaves_out_empty_fields(self):
        markdown = build_markdown(fields(title='', date='', content='Just text'))
        self.assertEqual(markdown, 'Just text')

    def test_reads_an_unquoted_date(self):
        draft = parse_draft('---\ndate: 2026-10-28\nwritten: 2026-10-30\n---\nHi')
        self.assertEqual((draft['date'], draft['written']), ('2026-10-28', '2026-10-30'))


class TestParsePostDate(unittest.TestCase):

    def test_frontmatter_date_wins_over_the_key(self):
        post = parse_post('2026/05/01/hello.md', '---\ndate: 2026-05-02\n---\nHi')
        self.assertEqual(post['date'], '2026-05-02')

    def test_falls_back_to_the_key(self):
        self.assertEqual(parse_post('2026/05/01/hello.md', 'Hi')['date'], '2026-05-01')
        self.assertEqual(parse_post('2026/05/01/hello.md', '---\ndate: whenever\n---\nHi')['date'], '2026-05-01')

    def test_written_is_when_it_was_written(self):
        post = parse_post('2019/07/28/trip.md', '---\ndate: 2019-07-28\nwritten: 2026-10-30\n---\nHi')
        self.assertEqual((post['date'], post['written']), ('2019-07-28', '2026-10-30'))

    def test_written_defaults_to_the_date(self):
        self.assertEqual(parse_post('2019/07/28/trip.md', 'Hi')['written'], '2019-07-28')
        post = parse_post('2019/07/28/trip.md', '---\ndate: 2019-07-29\nwritten: someday\n---\nHi')
        self.assertEqual(post['written'], '2019-07-29')


class TestTags(unittest.TestCase):

    def test_reads_a_list_or_a_comma_separated_string(self):
        self.assertEqual(frontmatter_tags(['Birds', 2026, None]), ['Birds', '2026'])
        self.assertEqual(frontmatter_tags('Birds, Road Trip,,'), ['Birds', 'Road Trip'])
        self.assertEqual(frontmatter_tags(None), [])

    def test_the_first_spelling_wins(self):
        self.assertEqual(frontmatter_tags(['Road Trip', 'road  trip', 'ROAD TRIP']), ['Road Trip'])

    def test_a_posts_tags(self):
        self.assertEqual(parse_post('2026/05/01/hello.md', '---\ntags: [Birds, Marsh]\n---\nHi')['tags'], ['Birds', 'Marsh'])
        self.assertEqual(parse_post('2026/05/01/hello.md', 'Hi')['tags'], [])


class TestDraftKeys(unittest.TestCase):

    def test_draft_id_from_key(self):
        self.assertEqual(draft_id_from_key(f'{PREFIX}draft.md'), DRAFT_ID)
        self.assertIsNone(draft_id_from_key(f'{PREFIX}birds/draft.md'))
        self.assertIsNone(draft_id_from_key('drafts/not-an-id/draft.md'))

    def test_photo_keys(self):
        self.assertEqual(draft_photo_key(DRAFT_ID, 'birds', 'a.jpg'), f'{PREFIX}birds/a.jpg')
        with self.assertRaises(UploadPathError):
            draft_photo_key(DRAFT_ID, 'birds', '../a.jpg')
        with self.assertRaises(UploadPathError):
            draft_photo_key(DRAFT_ID, 'birds', 'a.png')

    def test_draft_photo(self):
        self.assertEqual(draft_photo(DRAFT_ID, f'{PREFIX}photos/a.jpg'), {
            'key': f'{PREFIX}photos/a.jpg',
            'collection': 'photos',
            'filename': 'a.jpg',
            'ref': f'photo://{PREFIX}photos/a.jpg',
        })
        self.assertIsNone(draft_photo(DRAFT_ID, f'{PREFIX}draft.md'))
        self.assertIsNone(draft_photo(DRAFT_ID, f'{PREFIX}birds/nested/a.jpg'))
        self.assertIsNone(draft_photo(DRAFT_ID, 'birds/2026/10/28/a.jpg'))


class TestPlanPublish(unittest.TestCase):

    def test_files_the_post_and_its_photos_under_its_date(self):
        draft = fields(
            photo=f'photo://{PREFIX}photos/b.jpg',
            content=(
                f'`photo://{PREFIX}birds/a b.jpg`\n\n'
                '`photo://birds/2026/02/27/old.jpg`\n\n'
                f'![alt](photo://{PREFIX}photos/b.jpg)\n'
            ),
        )
        plan = plan_publish(DRAFT_ID, draft, [f'{PREFIX}birds/a b.jpg', f'{PREFIX}photos/b.jpg', f'{PREFIX}photos/unused.jpg'])

        self.assertEqual(plan['key'], '2026/10/28/marsh-morning.md')
        self.assertEqual(plan['slug'], 'marsh-morning')
        self.assertEqual(plan['photos'], {
            f'{PREFIX}birds/a b.jpg': 'birds/2026/10/28/a b.jpg',
            f'{PREFIX}photos/b.jpg': 'photos/2026/10/28/b.jpg',
            f'{PREFIX}photos/unused.jpg': 'photos/2026/10/28/unused.jpg',
        })
        post = parse_post(plan['key'], plan['markdown'])
        self.assertEqual(post['date'], '2026-10-28')
        self.assertEqual(post['written'], '2026-10-28')
        self.assertEqual(post['title'], 'Marsh Morning')
        self.assertEqual(post['photo'], 's3://spark.wiki.photos/photos/2026/10/28/b.jpg')
        self.assertEqual(post['content'], (
            '`photo://birds/2026/10/28/a b.jpg`\n\n'
            '`photo://birds/2026/02/27/old.jpg`\n\n'
            '![alt](photo://photos/2026/10/28/b.jpg)'
        ))

    def test_keeps_the_written_date(self):
        plan = plan_publish(DRAFT_ID, fields(date='2019-07-28', written='2026-10-30', tags=['Road Trip']), [])
        self.assertEqual(plan['key'], '2019/07/28/marsh-morning.md')
        post = parse_post(plan['key'], plan['markdown'])
        self.assertEqual((post['date'], post['written']), ('2019-07-28', '2026-10-30'))
        self.assertEqual(post['tags'], ['Road Trip'])

    def test_needs_a_title_and_date(self):
        for draft in (fields(title=''), fields(title='!!!'), fields(date='')):
            with self.assertRaises(DraftError):
                plan_publish(DRAFT_ID, draft, [])

    def test_refuses_to_embed_a_photo_thats_been_removed(self):
        with self.assertRaises(DraftError):
            plan_publish(DRAFT_ID, fields(content=f'`photo://{PREFIX}birds/gone.jpg`'), [])
        with self.assertRaises(DraftError):
            plan_publish(DRAFT_ID, fields(photo=f'photo://{PREFIX}birds/gone.jpg'), [])


if __name__ == '__main__':
    unittest.main()
