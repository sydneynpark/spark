import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.photo_upload_util import UploadPathError, deletable_folder  # noqa: E402
from utils.post_util import photo_refs  # noqa: E402


class TestDeletableFolder(unittest.TestCase):

    def test_date_folders_can_be_deleted(self):
        for prefix in ('2026/', '2026/07/', '2026/07/04/'):
            deletable_folder(prefix)

    def test_other_folders_cannot(self):
        # The collection's root, folders outside the date layout, and paths
        # that aren't folders at all.
        for prefix in ('', 'archive/', '2026/07/04/extra/', '2026/02/30/', '2026', '../2026/', '2026//'):
            with self.assertRaises(UploadPathError, msg=prefix):
                deletable_folder(prefix)


class TestPhotoRefs(unittest.TestCase):

    def test_embeds_in_body_and_frontmatter(self):
        markdown = (
            '---\n'
            'title: A day out\n'
            'photo: photo://photos/2026/07/04/2026-07-04 - Sunset.jpg\n'
            '---\n'
            'Look: ![Sunset](photo://photos/2026/07/04/2026-07-04 - Sunset.jpg)\n\n'
            '`photo://birds/2026/08/06/2026-08-06 - Anna\'s Hummingbird 05.jpg`\n'
        )
        self.assertEqual(photo_refs(markdown), {
            'photos/2026/07/04/2026-07-04 - Sunset.jpg',
            "birds/2026/08/06/2026-08-06 - Anna's Hummingbird 05.jpg",
        })

    def test_no_embeds(self):
        self.assertEqual(photo_refs('Just words, and a [link](https://example.com).'), set())


if __name__ == '__main__':
    unittest.main()
