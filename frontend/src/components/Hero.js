import React from 'react';

const Hero = () => {
  return (
    <section id="hero">
      <div className="hero-content">
        <div className="hero-text">
          <h2>Hi, I'm Sydney!</h2>
          <p>Welcome to my "personal wiki." This will be a place for me to share my bird photos and other random things.</p>
        </div>
        <div className="hero-image">
          <img 
            src="/images/profile.jpg" 
            alt="Sydney Park" 
            className="profile-photo"
          />
        </div>
      </div>
    </section>
  );
};

export default Hero;