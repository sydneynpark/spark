import frontmatter
from blog_metadata import BlogMetadata


class MarkdownUtil:
    def __init__(self):
        pass
    
    def find_metadata(self, markdown_content):
        # Parse frontmatter
        post = frontmatter.loads(markdown_content)
        
        blog_metadata = BlogMetadata(post)
        blog_metadata.debug_print()
        
        return blog_metadata
