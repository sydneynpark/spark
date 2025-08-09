import blog_metadata
import unittest
import aws_util
from unittest.mock import MagicMock
from datetime import datetime

class TestBlogMetadata(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_aws = aws_util.AWSUtil()
        blog_metadata.aws = self.mock_aws

    def test_directory_parsed_correctly(self):
        blog_post = blog_metadata.BlogPost("2025/08/01/My first blog post/content.md")
        self.assertEqual(blog_post.blog_post_directory, "2025/08/01/My first blog post")
        self.assertEqual(blog_post.title, "My first blog post")
        self.assertEqual(blog_post.published, datetime(2025, 8, 1).date())
        self.assertEqual(blog_post.updated, datetime.now().date())
        
        self.assertEqual(blog_post.content, None)
        self.assertEqual(blog_post.media, [])
        print(blog_post.to_dict())