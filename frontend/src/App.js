import React from 'react';
import './App.css';
import Header from './components/Header';
import Hero from './components/Hero';
import Content from './components/Content';
import Footer from './components/Footer';

function App() {
  return (
    <div className="App">
      <Header />
      <main>
        <Hero />
        <Content />
      </main>
      <Footer />
    </div>
  );
}

export default App;