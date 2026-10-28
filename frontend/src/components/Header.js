import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <header>
      <nav>
        <Link to="/" className="site-title" style={{textDecoration: 'none', color: 'inherit'}}>
          <span
            className="site-logo"
            aria-hidden="true"
            style={{'--logo-url': `url(${process.env.PUBLIC_URL}/favicon-192.png)`}}
          />
          <h1>Sydney Nicole Park</h1>
        </Link>
        <ul>
          <li><Link to="/">Home</Link></li>
          <li><Link to="/photos">Photos</Link></li>
          <li><Link to="/birds">Birds</Link></li>
          <li><Link to="/blog">Blog</Link></li>
          <li><Link to="/books">Books</Link></li>
        </ul>
      </nav>
    </header>
  );
};

export default Header;