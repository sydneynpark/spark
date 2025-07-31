import React from 'react';

const Content = () => {
  return (
    <section id="content">
      <div className="card">
        <h3>About This Site</h3>
        <p>
          This is a simple "hello world" React frontend for my bird photography blog. 
          Soon it will display amazing bird photos and blog posts about birding adventures.
        </p>
      </div>

      <div className="card">
        <h3>Coming Soon</h3>
        <ul>
          <li>📸 Bird photo gallery with taxonomic classifications</li>
          <li>📝 Blog posts about birding experiences</li>
          <li>🔍 Search and filter by species, family, and order</li>
          <li>🗂️ Organized content management</li>
        </ul>
      </div>
    </section>
  );
};

export default Content;