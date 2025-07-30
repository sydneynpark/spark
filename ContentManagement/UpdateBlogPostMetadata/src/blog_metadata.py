class BlogMetadata:
    def __init__(self, post):
        metadata_dict = post.metadata
        self.title = metadata_dict.get('title', '')
        self.publish_date = metadata_dict.get('publish_date', '')
        self.author = metadata_dict.get('author', '')
        self.tags = metadata_dict.get('tags', [])
        self.summary = metadata_dict.get('summary', '')
        self.featured_image = metadata_dict.get('featured_image', '')
        self.content_preview = post.content[:200] + '...' if len(post.content) > 200 else post.content
    
    def __str__(self):
        return f"BlogMetadata(title='{self.title}', author='{self.author}', publish_date='{self.publish_date}')"
    
    def __repr__(self):
        return self.__str__()

    def debug_print(self):
        print('=== Blog Post Metadata ===')
        print(f'Title: {self.title or "No title"}')
        print(f'Publish Date: {self.publish_date or "No date"}')
        print(f'Author: {self.author or "No author"}')
        print(f'Tags: {self.tags}')
        print(f'Summary: {self.summary or "No summary"}')
        print(f'Featured Image: {self.featured_image or "No featured image"}')

        print('=== Content Preview ===')
        print(self.content_preview)
