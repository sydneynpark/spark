import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Hero from './components/Hero';
import Content from './components/Content';
import Photos from './components/Photos';
import Gallery from './components/Gallery';
import Blog from './components/Blog';
import BlogPost from './components/BlogPost';
import Books from './components/Books';
import BookReview from './components/BookReview';
import Footer from './components/Footer';
import AdminLogin from './components/admin/AdminLogin';
import AdminDashboard from './components/admin/AdminDashboard';
import AdminRoute from './components/admin/AdminRoute';
import BookReviewForm from './components/admin/BookReviewForm';
import PhotoUploader from './components/admin/PhotoUploader';

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
            <Route path="/gallery" element={<Gallery />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/blog/:postId" element={<BlogPost />} />
            <Route path="/books" element={<Books />} />
            <Route path="/books/:title" element={<BookReview />} />
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
            <Route path="/admin/books/new" element={<AdminRoute><BookReviewForm /></AdminRoute>} />
            <Route path="/admin/photos/upload" element={<AdminRoute><PhotoUploader /></AdminRoute>} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;