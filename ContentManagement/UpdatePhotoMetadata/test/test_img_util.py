
import unittest
from unittest.mock import MagicMock
import test.sample_events as sample_events
import img_util


class TestImageUtil(unittest.TestCase):
    
    def setUp(self) -> None:
        self.img_util = img_util.ImageUtil()

    def test_get_exif(self):
        test_img = sample_events.TreeSwallowPhoto
        found_keywords = self.img_util.get_lightroom_keywords(test_img)

        for kword in ['Birds', 'Hirundinidae', 'PASSERIFORMES', 'Swallows- Martins', 'Tachycineta bicolor', 'Tree Swallow']:
            assert kword in found_keywords

    def test_get_date_captured(self):
        # A fresh stream, since TreeSwallowPhoto is a shared module-level
        # StreamingBody and test_get_exif already reads it to EOF.
        test_img = sample_events.file_to_streamingbody('tree-swallow')
        date_captured = self.img_util.get_date_captured(test_img)

        # DateTimeOriginal is 2025:05:17 09:51:56; the top-level DateTime tag
        # is 2025:05:20 (Lightroom's export date) and must not be used instead.
        assert date_captured == '2025-05-17'

if __name__ == '__main__':
    unittest.main()
