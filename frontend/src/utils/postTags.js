// Tags match regardless of case, as the backend dedupes them
// (post_util.frontmatter_tags).

export function hasTag(post, tag) {
  return (post.tags || []).some(t => t.toLowerCase() === tag.toLowerCase());
}

// The tags `posts` have, each with how many have it, most used first (then
// A-Z). Differently cased spellings of one count as one, the first seen.
export function tagsInUse(posts) {
  const counts = new Map();
  posts.forEach(post => (post.tags || []).forEach(tag => {
    const key = tag.toLowerCase();
    const entry = counts.get(key) || { tag, count: 0 };
    entry.count += 1;
    counts.set(key, entry);
  }));
  return [...counts.values()].sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}
