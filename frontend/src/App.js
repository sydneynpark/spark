import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Hero from './components/Hero';
import Content from './components/Content';
import Birds from './components/Birds';
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
import DraftList from './components/admin/DraftList';
import PostEditor from './components/admin/PostEditor';
import { usePageTitle } from './utils/pageTitle';

function Home() {
  usePageTitle();
  return (
    <>
      <Hero />
      <Content />
    </>
  );
}

// Where the bird photos' gallery used to be, before /photos was for the rest.
function OldBirdsGallery() {
  const { search } = useLocation();
  return <Navigate to={`/birds/gallery${search}`} replace />;
}

function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/photos" element={<Photos />} />
            <Route path="/photos/gallery" element={<Gallery key="photos" collection="photos" />} />
            <Route path="/birds" element={<Birds />} />
            <Route path="/birds/gallery" element={<Gallery key="birds" collection="birds" />} />
            <Route path="/gallery" element={<OldBirdsGallery />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/blog/:slug" element={<BlogPost />} />
            <Route path="/books" element={<Books />} />
            <Route path="/books/:title" element={<BookReview />} />
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
            <Route path="/admin/books/new" element={<AdminRoute><BookReviewForm /></AdminRoute>} />
            <Route path="/admin/photos/upload" element={<AdminRoute><PhotoUploader key="photos" collection="photos" /></AdminRoute>} />
            <Route path="/admin/birds/upload" element={<AdminRoute><PhotoUploader key="birds" collection="birds" /></AdminRoute>} />
            <Route path="/admin/posts" element={<AdminRoute><DraftList /></AdminRoute>} />
            {/* :draftId is "new" for a post not saved yet. */}
            <Route path="/admin/posts/:draftId" element={<AdminRoute><PostEditor /></AdminRoute>} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;