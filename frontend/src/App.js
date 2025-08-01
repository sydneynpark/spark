import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Hero from './components/Hero';
import Content from './components/Content';
import Photos from './components/Photos';
import Footer from './components/Footer';

function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={
              <>
                <Hero />
                <Content />
              </>
            } />
            <Route path="/photos" element={<Photos />} />
            <Route path="/blog" element={
              <div style={{textAlign: 'center', padding: '2rem'}}>
                <h2>Blog</h2>
                <p>Blog posts coming soon!</p>
              </div>
            } />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;