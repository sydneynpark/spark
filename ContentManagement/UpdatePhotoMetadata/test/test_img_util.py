
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

if __name__ == '__main__':
    unittest.main()
