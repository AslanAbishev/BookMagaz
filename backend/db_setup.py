import pandas as pd
from pymongo import MongoClient, TEXT
import os


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["goodbooks"]


def load_books():
    print("Loading books...")
    df = pd.read_csv("data/books.csv")
    db.books.drop()
    
    # Ensure required fields exist for assignment requirements
    records = df.to_dict("records")
    for record in records:
        # Add price if missing (generate based on average_rating or use default)
        if "price" not in record or pd.isna(record.get("price")):
            base_price = 9.99
            if "average_rating" in record and not pd.isna(record.get("average_rating")):
                # Higher rated books cost more
                record["price"] = round(base_price + (record["average_rating"] - 3) * 2, 2)
            else:
                record["price"] = base_price
        
        # Add category if missing (derive from other fields or use default)
        if "category" not in record or pd.isna(record.get("category")):
            # Try to extract category from title/authors or use a default
            categories = ["Fiction", "Non-Fiction", "Mystery", "Romance", "Science Fiction", 
                         "Fantasy", "Biography", "History", "Self-Help", "Business"]
            # Simple hash-based category assignment for consistency
            record["category"] = categories[hash(record.get("title", "")) % len(categories)]
        
        # Ensure description exists (use title/author info if missing)
        if "description" not in record or pd.isna(record.get("description")):
            desc = f"A captivating book by {record.get('authors', 'Unknown Author')}. "
            desc += f"This book has an average rating of {record.get('average_rating', 'N/A')} "
            desc += f"based on {record.get('ratings_count', 0)} ratings."
            record["description"] = desc
        
        # Generate book cover image URL
        # Try to use ISBN for Open Library covers, otherwise use placeholder
        isbn = record.get("isbn") or record.get("isbn13") or record.get("ISBN") or record.get("ISBN13")
        if isbn and not pd.isna(isbn):
            # Remove any dashes or spaces from ISBN
            isbn_clean = str(isbn).replace("-", "").replace(" ", "")
            # Open Library Covers API
            record["image_url"] = f"https://covers.openlibrary.org/b/isbn/{isbn_clean}-L.jpg"
        else:
            # Use a nice placeholder service with book title
            title_encoded = str(record.get("title", "Book")).replace(" ", "+")[:50]
            # Using placeholder.com with book theme, or usecovers.com
            record["image_url"] = f"https://placehold.co/300x450/667eea/ffffff?text={title_encoded}"
        
        # Convert NaN to None for MongoDB
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
    
    db.books.insert_many(records)
    
    # Create indexes
    try:
        # Text index for full-text search (may fail if text fields don't exist)
        db.books.create_index([("title", TEXT), ("authors", TEXT)])
        print("Text index created successfully")
    except Exception as e:
        print(f"Warning: Could not create text index: {e}")
        print("   Will use regex search as fallback")
    
    # Create other indexes
    db.books.create_index("category")
    db.books.create_index("book_id")
    db.books.create_index("average_rating")
    
    # Create compound indexes for better performance
    db.books.create_index([("category", 1), ("average_rating", -1)])
    
    print(f"Books loaded! Total: {len(records)}")


def load_ratings():
    print("Loading ratings...")
    df = pd.read_csv("data/ratings.csv")
    df.rename(columns={"user_id": "user_id", "book_id": "book_id", "rating": "rating"}, inplace=True)

    db.interactions.drop()
    records = df.to_dict("records")
    db.interactions.insert_many(records)
    print("Ratings loaded!")


def build_users():
    print("Building users collection...")
    db.users.drop()
    user_ids = db.interactions.distinct("user_id")

    for uid in user_ids:
        db.users.insert_one({"username": str(uid), "password": "placeholder"})

    print("Users created!")


if __name__ == "__main__":
    load_books()
    load_ratings()
    build_users()
    print("DB setup complete!")
