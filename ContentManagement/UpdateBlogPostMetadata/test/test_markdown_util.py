import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from markdown_util import MarkdownUtil

class TestMarkdownUtil(unittest.TestCase):
    
    def test_sample_post_metadata_parsing(self):
        # Read the sample markdown file
        test_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'sample-post.md')
        with open(test_file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Parse the markdown
        markdown_util = MarkdownUtil()
        metadata = markdown_util.find_metadata(markdown_content)
        
        # Verify metadata
        self.assertEqual(metadata.title, 'Hello World')
        self.assertEqual(metadata.publish_date, '2025-07-29')
        self.assertEqual(metadata.author, 'Sydney Park')
        self.assertEqual(metadata.tags, ['technology', 'blog'])
        self.assertEqual(metadata.summary, "I have never had a blog before. This is my first blog post ever!")
        
        # Verify content exists and starts correctly
        self.assertTrue(metadata.content_preview.startswith('# Hello world!'))
        self.assertIn('Hi everybody. My name is Sydney Park.', metadata.content_preview)

if __name__ == '__main__':
    unittest.main()