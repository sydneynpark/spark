import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <header>
      <nav>
        <Link to="/" style={{textDecoration: 'none', color: 'inherit'}}>
          <h1>Spark.Wiki</h1>
        </Link>
        <ul>
          <li><Link to="/">Home</Link></li>
          <li><Link to="/photos">Photos</Link></li>
          <li><Link to="/blog">Blog</Link></li>
        </ul>
      </nav>
    </header>
  );
};

export default Header;