from bson import ObjectId
from datetime import datetime


def get_user_by_username(db, username):
    return db.users.find_one({"username": username})


def get_user_by_email(db, email):
    """Get user by email address"""
    if not email:
        return None
    return db.users.find_one({"email": email.strip().lower()})


def get_user_by_id(db, user_id):
    try:
        return db.users.find_one({"_id": ObjectId(user_id)})
    except:
        return None


def create_user(db, username, hashed_password, email=None, name=None):
    if not email:
        raise ValueError("Email is required")
    
    user = {
        "username": username,
        "password": hashed_password,
        "email": email.strip().lower(),  # Store email in lowercase
        "name": name or "",
        "created_at": datetime.utcnow(),
        "preferences": {
            "categories": [],
            "favorite_authors": []
        },
        "reset_token": None,
        "reset_token_expiry": None
    }
    result = db.users.insert_one(user)
    return result.inserted_id


def update_user_profile(db, user_id, **kwargs):
    """Update user profile fields"""
    update_data = {}
    if "email" in kwargs:
        update_data["email"] = kwargs["email"]
    if "name" in kwargs:
        update_data["name"] = kwargs["name"]
    if "preferences" in kwargs:
        update_data["preferences"] = kwargs["preferences"]
    
    if update_data:
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})


def insert_interaction(db, user_id, book_id, interaction, rating=None):
    interaction_doc = {
        "user_id": str(user_id),
        "book_id": int(book_id),
        "interaction": interaction,  # 'view', 'like', 'purchase', 'rating'
        "rating": float(rating) if rating is not None else None,
        "timestamp": datetime.utcnow()
    }
    db.interactions.insert_one(interaction_doc)


def get_user_interactions(db, user_id, interaction_type=None):
    """Get all interactions for a user, optionally filtered by type"""
    query = {"user_id": str(user_id)}
    if interaction_type:
        query["interaction"] = interaction_type
    return list(db.interactions.find(query).sort("timestamp", -1))


def get_user_purchase_history(db, user_id):
    """Get user's purchase history"""
    return get_user_interactions(db, user_id, "purchase")


def get_user_ratings(db, user_id):
    """Get all ratings by a user"""
    return list(db.interactions.find({
        "user_id": str(user_id),
        "rating": {"$ne": None}
    }).sort("timestamp", -1))


def get_book(db, book_id):
    return db.books.find_one({"book_id": int(book_id)})


def search_books(db, text, category=None, limit=30):
    """Search books by text, optionally filtered by category"""
    query = {}
    
    # Build query based on category
    if category and category.strip():
        query["category"] = category.strip()
    
    # Text search - try $text first, fallback to regex if it fails
    if text and text.strip():
        text = text.strip()
        
        # Fallback to regex search (case-insensitive) - more reliable
        # Search in title and authors using regex
        text_query = {"$or": [
            {"title": {"$regex": text, "$options": "i"}},
            {"authors": {"$regex": text, "$options": "i"}}
        ]}
        
        # Merge with category query if exists
        if query:
            query = {"$and": [text_query, query]}
        else:
            query = text_query
        
        # Note: Using regex search by default as it's more reliable
        # MongoDB text search requires specific text index setup
    
    # Execute the query
    try:
        if query:
            results = list(db.books.find(query).limit(limit))
        else:
            # No query means return all books
            results = list(db.books.find().limit(limit))
        
        return results
    except Exception as e:
        print(f"ERROR in search_books: {e}")
        import traceback
        print(traceback.format_exc())
        # If query fails completely, return empty
        return []


def get_books_by_category(db, category, limit=30):
    """Get books in a specific category"""
    return list(db.books.find({"category": category}).limit(limit))


def get_all_categories(db):
    """Get all unique categories"""
    try:
        return sorted([c for c in db.books.distinct("category") if c])
    except:
        return []


def get_popular_books(db, limit=10):
    """Get popular books based on average rating"""
    return list(db.books.find({
        "average_rating": {"$exists": True, "$ne": None},
        "ratings_count": {"$exists": True, "$gte": 100}
    }).sort([("average_rating", -1), ("ratings_count", -1)]).limit(limit))


def check_user_interaction(db, user_id, book_id, interaction_type):
    """Check if a user has a specific interaction with a book"""
    return db.interactions.find_one({
        "user_id": str(user_id),
        "book_id": int(book_id),
        "interaction": interaction_type
    })


def set_password_reset_token(db, email, token, expiry):
    """Set password reset token for user"""
    db.users.update_one(
        {"email": email.strip().lower()},
        {"$set": {
            "reset_token": token,
            "reset_token_expiry": expiry
        }}
    )


def get_user_by_reset_token(db, token):
    """Get user by reset token if valid"""
    user = db.users.find_one({
        "reset_token": token,
        "reset_token_expiry": {"$gt": datetime.utcnow()}
    })
    return user


def update_user_password(db, user_id, new_hashed_password):
    """Update user password and clear reset token"""
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "password": new_hashed_password,
            "reset_token": None,
            "reset_token_expiry": None
        }}
    )
