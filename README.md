# GoodBooks - Book Recommendation Platform

A modern, full-featured book recommendation e-commerce platform built with Flask, MongoDB, and collaborative filtering algorithms.

## 🎯 Project Overview

GoodBooks is a NoSQL database project that demonstrates:
- User registration and profile management
- Product catalog with categories and search
- Collaborative filtering recommendation engine
- User interaction tracking (views, likes, purchases, ratings)
- Purchase history
- Performance-optimized database queries

## ✨ Features

### Core Features (Assignment Requirements)

1. **User Registration and Profiles**
   - User registration with email and name
   - Profile management and editing
   - Secure password hashing

2. **Product Catalog**
   - Comprehensive book database with:
     - Title, authors, description
     - Category classification
     - Price information
     - Average ratings and rating counts
   - Browse by category
   - Popular books section

3. **User History**
   - Track purchase history
   - View interaction history (views, likes, ratings)
   - Display user ratings

4. **Recommendation Engine**
   - Item-based collaborative filtering
   - Personalized recommendations based on user ratings
   - Cold-start handling (popular books for new users)
   - Recommendation score display

5. **Collaborative Filtering**
   - Cosine similarity-based item recommendations
   - User-based preference matching
   - Similarity matrix caching for performance

6. **Search Functionality**
   - Full-text search by title and author
   - Category filtering
   - Real-time AJAX search results

7. **NoSQL Database (MongoDB)**
   - Optimized data modeling for books, users, and interactions
   - Indexed queries for performance
   - Efficient document structure

8. **Data Modeling**
   - Books collection with flexible schema
   - Users collection with preferences
   - Interactions collection tracking all user actions

9. **RESTful API**
   - `/api/search` - Search books
   - `/api/interact` - Record interactions
   - `/api/rate` - Rate books
   - `/api/like` - Like/unlike books
   - `/api/purchase` - Record purchases
   - `/api/recommend/<user_id>` - Get recommendations
   - `/api/categories` - Get all categories
   - `/api/user/interactions` - Get user interactions

10. **User Interface**
    - Modern, responsive design
    - Mobile-friendly layout
    - Intuitive navigation
    - Beautiful book cards and product pages

11. **Performance Testing**
    - Performance testing script included
    - Query optimization
    - Index recommendations
    - Database statistics

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, Flask
- **Database**: MongoDB 7.0
- **Machine Learning**: scikit-learn, pandas, numpy
- **Frontend**: HTML5, CSS3, JavaScript
- **Containerization**: Docker, Docker Compose

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB 7.0 (or use Docker)
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   cd goodbooks_app
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Set up MongoDB**
   
   Option A: Using Docker (Recommended)
   ```bash
   docker-compose up -d
   ```
   
   Option B: Local MongoDB
   - Install MongoDB locally
   - Ensure it's running on `localhost:27017`

5. **Load data into MongoDB**
   ```bash
   python db_setup.py
   ```
   
   This will:
   - Load books from `data/books.csv`
   - Load ratings from `data/ratings.csv`
   - Create indexes for optimal performance
   - Add price and category fields if missing

6. **Build similarity matrix**
   ```bash
   python -c "from recommend import build_item_similarity; from pymongo import MongoClient; import os; client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/')); db = client['goodbooks']; build_item_similarity(db, force_rebuild=True)"
   ```
   
   Or access via admin route after starting the app:
   ```
   http://localhost:5000/admin/rebuild-sim
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

8. **Access the application**
   - Open your browser to `http://localhost:5000`

## 🧪 Performance Testing

Run the performance testing suite:

```bash
cd backend
python performance_test.py
```

This will test:
- Database query performance
- Recommendation generation speed
- Search functionality
- Interaction queries
- Similarity matrix build time

## 📁 Project Structure

```
goodbooks_app/
├── backend/
│   ├── app.py                 # Flask application and routes
│   ├── models.py              # Database models and queries
│   ├── recommend.py           # Recommendation engine
│   ├── db_setup.py            # Database setup script
│   ├── performance_test.py    # Performance testing script
│   ├── requirements.txt       # Python dependencies
│   └── templates/             # HTML templates
│       ├── base.html
│       ├── index.html
│       ├── login.html
│       ├── register.html
│       ├── product.html
│       ├── profile.html
│       ├── edit_profile.html
│       ├── history.html
│       └── category.html
├── static/
│   └── style.css             # Modern CSS styling
├── data/
│   ├── books.csv             # Book dataset
│   └── ratings.csv           # Ratings dataset
├── docker-compose.yml        # MongoDB container setup
└── README.md                 # This file
```

## 🔐 Environment Variables

Create a `.env` file in the backend directory (optional):

```env
MONGO_URI=mongodb://localhost:27017/
SECRET_KEY=your-secret-key-here
```

## 🚀 Usage Guide

### For Users

1. **Register/Login**
   - Create an account or login with existing credentials

2. **Browse Books**
   - Browse the catalog on the home page
   - Use search to find specific books
   - Filter by category

3. **Interact with Books**
   - View book details
   - Rate books (1-5 stars)
   - Like books you enjoy
   - Record purchases

4. **Get Recommendations**
   - Visit your profile page
   - See personalized recommendations based on your ratings
   - Check recommendation scores

5. **View History**
   - Check purchase history
   - Review your ratings
   - See liked books

### For Developers

#### Adding New Features

1. **Add new API endpoints** in `backend/app.py`
2. **Create database queries** in `backend/models.py`
3. **Enhance recommendations** in `backend/recommend.py`

#### Database Schema

**Books Collection:**
```javascript
{
  book_id: Integer,
  title: String,
  authors: String,
  category: String,
  price: Float,
  description: String,
  average_rating: Float,
  ratings_count: Integer
}
```

**Users Collection:**
```javascript
{
  username: String,
  password: String (hashed),
  email: String,
  name: String,
  created_at: DateTime,
  preferences: {
    categories: Array,
    favorite_authors: Array
  }
}
```

**Interactions Collection:**
```javascript
{
  user_id: String,
  book_id: Integer,
  interaction: String, // 'view', 'like', 'purchase', 'rating'
  rating: Float, // Only for 'rating' interaction
  timestamp: DateTime
}
```

## 📊 Performance Optimization

1. **Database Indexes**
   - `book_id` - Fast book lookups
   - `category` - Category filtering
   - `(title, authors)` - Full-text search
   - `user_id` - User interaction queries
   - `(user_id, book_id)` - Compound index for user-book lookups

2. **Similarity Matrix Caching**
   - Pre-computed similarity matrix saved to `data/sim_cache.pkl`
   - Rebuild periodically as new ratings are added

3. **Query Optimization**
   - Limit result sets
   - Use indexes appropriately
   - Pagination for large datasets

## 🐛 Troubleshooting

**Issue: MongoDB connection error**
- Ensure MongoDB is running
- Check `MONGO_URI` environment variable
- For Docker: `docker-compose up -d`

**Issue: No recommendations**
- Ensure ratings data is loaded
- Build similarity matrix: `/admin/rebuild-sim`
- Check that users have ratings

**Issue: Search not working**
- Ensure text index is created: `db.books.createIndex({title: "text", authors: "text"})`
- Re-run `db_setup.py`

## 📝 Assignment Requirements Checklist

- ✅ User Registration and Profiles
- ✅ Product Catalog (with name, description, category, price)
- ✅ User History (purchase history and interactions)
- ✅ Recommendation Engine
- ✅ Collaborative Filtering (item-based)
- ✅ Search Functionality
- ✅ NoSQL Database (MongoDB)
- ✅ Data Modeling
- ✅ RESTful API
- ✅ User Interface
- ✅ Performance Testing

## 🔄 Future Enhancements

- User-based collaborative filtering
- Content-based filtering
- Hybrid recommendation approaches
- Real-time recommendation updates
- Advanced analytics dashboard
- Social features (reviews, comments)
- Wishlist functionality
- Email notifications

## 📄 License

This project is created for educational purposes as part of a database course assignment.

## 👤 Author

Created for Assignment #6 - NoSQL Database Course

---

**Note**: Make sure to run `db_setup.py` after cloning to populate the database with sample data.
