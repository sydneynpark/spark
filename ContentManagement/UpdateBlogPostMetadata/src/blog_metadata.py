import frontmatter
from abc import ABC, abstractmethod
from datetime import datetime
import aws_util


aws = aws_util.AWSUtil()

DATE_FORMAT = "%Y/%m/%d"
S3_BUCKET = "spark.wiki.blog"

class BlogPost:

    def __init__(self, s3_key):
        '''
        Represents a Blog Post, which is a collection of content intended to be bundled into one "article."
        
        S3 content is organized using the following naming convention:
        <bucket>/YYYY/MM/DD/<Blog post title>/
        
        Inside of this directory is where all blog post content will be stored
        Example:
         - 2025/08/01/My first blog post/content.md
         - 2025/08/01/My first blog post/img1.jpg
         - 2025/08/01/My first blog post/864A8351.jpg
        '''
        
        self.updated = datetime.now().date()
        self.title = "Untitled article"
        self.published = self.updated
        self.content = None
        self.media = []

        # Remove name of individual file to find blog post directory
        # Before: "2025/08/01/My first blog post/content.md"
        # After:  "2025/08/01/My first blog post"
        self.blog_post_directory = s3_key.strip('/').rsplit('/', 1)[0]

        # Split dir into: ["2025/08/01", "My first blog post"]
        parts = self.blog_post_directory.rsplit('/', 1)

        if len(parts) == 2:
            self.title = parts[1]
            try:
                self.published = datetime.strptime(parts[0], DATE_FORMAT).date()
            except Exception:
                print(f'Couldn\'t parse publication date from {s3_key}')
                pass
        else:
            print(f'Invalid S3 key format!! Using default title/published for blog post at {s3_key}')

    def to_dict(self):
        return {
            'blog_post_directory': self.blog_post_directory,
            'title': self.title,
            'published': self.published,
            'updated': self.updated,
            'content': self.content,
            'media': self.media
        }

    def write(self, s3_key):
        # TODO check if there is already an entry in the blog_posts Dynamo table for this post
        # TODO if there isn't, create one
        # A blog post object is shaped like this:
        # {
        #   "blog_post_directory": "<s3 path of the folder containing all blog post content>",
        #   "title": "<Title extracted from the bottom-most folder>",
        #   "published": <date extracted from s3 path>,
        #   "updated": <current date>,
        #   "content": <a BlogPostContent object>,
        #   "media": [ <an arbitrary number of BlogPostMedia objects> ]
        # }
        pass


class BlogPostContent(ABC):

    def __init__(self, s3_key):
        self.blog_post = BlogPost(s3_key)

    @staticmethod
    def from_s3_key(s3_key):
        # Get lowercase version of file extension
        ext = s3_key.split('.')[-1].lower()
        # If s3 key is a markdown file, then read it as a BlogMetadata
        if ext == 'md':
            return BlogMetadata(s3_key)
        elif ext == 'jpg':
            return BlogPostMedia(s3_key)
        else:
            raise ValueError(f'Aaaaahhh! I don\'t know how to deal with {ext} files yet!')

    @abstractmethod
    def to_dict(self):
        pass

    # @abstractmethod
    # def store(self):
    #     pass # Implementing classes will decide how/where their content is stored


class BlogMetadata(BlogPostContent):
    def __init__(self, s3_key):
        super().__init__(s3_key)
        
        response = aws.get_s3_object(S3_BUCKET, s3_key)
        markdown_content = response['Body'].read().decode('utf-8')

        post = frontmatter.loads(markdown_content)
        
        metadata_dict = post.metadata
        self.tags = metadata_dict.get('tags', [])
        self.summary = metadata_dict.get('summary', '')
        self.content_preview = post.content[:200] + '...' if len(post.content) > 200 else post.content
    
    def to_dict(self):
        return {
            'tags': self.tags,
            'summary': self.summary,
            'content_preview': self.content_preview
        }

    def __str__(self):
        return '\n'.join([
            '=== Blog Post Metadata ===',
            f'Tags: {self.tags}',
            f'Summary: {self.summary or "No summary"}',
            '',
            '=== Content Preview ===',
            self.content_preview
        ])

    
    def debug_print(self):
        print(self)

class BlogPostMedia(BlogPostContent):
    pass