import frontmatter
from abc import ABC, abstractmethod


class BlogPost:
    def __init__(self, s3_key):
        # S3 content is organized using the following naming convention:
        # spark.wiki.blog/YYYY/MM/DD/<Blog post title>/
        # Inside of this directory is where all blog post content will be stored
        # TODO extract the title from s3_key and store as an instance variable self.slug
        # TODO extract the post date from s3_key and store as an instance variable self.published
        # TODO check if there is already an entry in the blog_posts Dynamo table for this post
        # TODO if there isn't, create one
        # A blog post object is shaped like this:
        # {
        #   "s3_location": "<s3 path of the folder containing all blog post content>",
        #   "title": "<Title extracted from the bottom-most folder>",
        #   "published": <date extracted from s3 path>,
        #   "updated": <current date>,
        #   "content": <a BlogPostContent object>,
        #   "media": [ <an arbitrary number of BlogPostMedia objects> ]
        # }
        pass
    
    def write(self, s3_key):
        pass


class BlogPostContent(ABC):

    def __init__(self, s3_key):
        pass


    # @abstractmethod
    # def store(self):
    #     pass # Implementing classes will decide how/where their content is stored


class BlogMetadata(BlogPostContent):
    def __init__(self, markdown_content):
        post = frontmatter.loads(markdown_content)
        
        metadata_dict = post.metadata
        self.tags = metadata_dict.get('tags', [])
        self.summary = metadata_dict.get('summary', '')
        self.content_preview = post.content[:200] + '...' if len(post.content) > 200 else post.content
    
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