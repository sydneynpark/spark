import React from 'react';
import { Link } from 'react-router-dom';

function PostCard({ post }) {
  return (
    <li className="post-item">
      <Link to={`/blog/${post.id}`}>
        <h3>{post.title}</h3>
        {post.date && <time>{post.date}</time>}
        {post.preview && <p className="post-preview">{post.preview}</p>}
      </Link>
    </li>
  );
}

export default PostCard;
