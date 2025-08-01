import React from 'react';

const Content = () => {
  return (
    <section id="content">
      <div className="card">
        <h3>About Me</h3>
        <p>
          I'm a software engineer in southeast Wisconsin. 
        </p>
        <p>
          Sometimes I play video games, bake sourdough bread, lift gigantic weights, or take photos of birds.
        </p>
      </div>

      <div className="card">
        <h3>What You'll Find Here</h3>
        <ul>
          <li>Bird photo gallery with (attempted) species idenfitications</li>
          <li>Some blog posts, maybe</li>
          <li>I'm not sure what else</li>
        </ul>
      </div>
    </section>
  );
};

export default Content;