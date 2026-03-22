import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os


CACHE_FILE = "data/sim_cache.pkl"
TOP_K = 15  # neighbors per item


def build_item_similarity(db, force_rebuild=False):
    if os.path.exists(CACHE_FILE) and not force_rebuild:
        return

    print("Building similarity matrix...")

    ratings = list(db.interactions.find({"rating": {"$ne": None}}))

    if not ratings:
        print("No ratings found. Cannot build similarity.")
        return

    df = pd.DataFrame(ratings)
    df["rating"] = df["rating"].astype(float)

    user_item = df.pivot_table(index="user_id", columns="book_id", values="rating")

    similarity = cosine_similarity(user_item.fillna(0).T)
    similarity_df = pd.DataFrame(similarity, index=user_item.columns, columns=user_item.columns)

    with open(CACHE_FILE, "wb") as f:
        pickle.dump(similarity_df, f)

    print("Similarity matrix built!")


def get_recommendations(user_id, db):
    """Get personalized recommendations using hybrid approach: collaborative + content-based"""
    if not os.path.exists(CACHE_FILE):
        build_item_similarity(db)

    with open(CACHE_FILE, "rb") as f:
        similarity_df = pickle.load(f)

    ratings = list(db.interactions.find({"user_id": user_id, "rating": {"$ne": None}}))
    
    # Get books user has already rated/interacted with (exclude these)
    rated_book_ids = [r["book_id"] for r in ratings]
    
    # Get user's preferred genres from their ratings
    user_rated_books = [db.books.find_one({"book_id": bid}) for bid in rated_book_ids]
    user_categories = {}
    user_authors = {}
    
    for book in user_rated_books:
        if book:
            category = book.get("category")
            author = book.get("authors")
            if category:
                user_categories[category] = user_categories.get(category, 0) + 1
            if author:
                # Handle multiple authors
                authors_list = [a.strip() for a in str(author).split(",")]
                for a in authors_list:
                    user_authors[a] = user_authors.get(a, 0) + 1

    if not ratings:
        # Cold start → popular books in user's preferred categories (if any)
        if user_categories:
            top_category = max(user_categories.items(), key=lambda x: x[1])[0]
            books = list(db.books.find({"category": top_category})
                        .sort("average_rating", -1).limit(10))
        else:
            books = list(db.books.find().sort("average_rating", -1).limit(10))
        return [{"book_id": b["book_id"], "title": b["title"], "authors": b["authors"],
                "average_rating": b.get("average_rating"), "category": b.get("category"),
                "price": b.get("price")} for b in books]

    scores = {}

    # COLLABORATIVE FILTERING: Use similarity from ratings
    for r in ratings:
        book_id = r["book_id"]
        user_rating = r["rating"]

        if book_id not in similarity_df.index:
            continue

        sim_scores = similarity_df[book_id].sort_values(ascending=False)[1:TOP_K+1]

        for similar_item, sim_value in sim_scores.items():
            if similar_item not in rated_book_ids:  # Don't recommend already rated
                scores[similar_item] = scores.get(similar_item, 0) + sim_value * user_rating

    # CONTENT-BASED BOOST: Add genre/category similarity
    # Boost books in same categories as user's highly rated books
    for r in ratings:
        rated_book_id = r["book_id"]
        user_rating = r["rating"]
        
        if user_rating >= 4:  # Only boost from highly rated books
            rated_book = db.books.find_one({"book_id": rated_book_id})
            if not rated_book:
                continue
            
            category = rated_book.get("category")
            author = rated_book.get("authors")
            
            # Boost books in same category (limit to top 10 per category)
            if category:
                same_category_books = list(db.books.find({
                    "category": category,
                    "book_id": {"$nin": rated_book_ids}
                }).sort("average_rating", -1).limit(10))
                for book in same_category_books:
                    similar_book_id = book["book_id"]
                    # Boost score for genre match (only for highly rated books in category)
                    if book.get("average_rating", 0) >= 3.5:  # Only boost well-rated books
                        genre_boost = 0.3 * user_rating  # 30% boost for genre match
                        scores[similar_book_id] = scores.get(similar_book_id, 0) + genre_boost
            
            # Boost books by same author
            if author:
                author_main = author.split(",")[0].strip()
                same_author_books = list(db.books.find({
                    "authors": {"$regex": author_main, "$options": "i"},
                    "book_id": {"$nin": rated_book_ids, "$ne": rated_book_id}
                }))
                for book in same_author_books[:5]:  # Limit to 5 per author
                    similar_book_id = book["book_id"]
                    author_boost = 0.2 * user_rating  # 20% boost for author match
                    scores[similar_book_id] = scores.get(similar_book_id, 0) + author_boost

    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

    result = []
    for book_id, score in top:
        b = db.books.find_one({"book_id": book_id})
        if b:
            result.append({
                "book_id": b["book_id"],
                "title": b["title"], 
                "authors": b["authors"],
                "average_rating": b.get("average_rating"),
                "category": b.get("category"),
                "price": b.get("price"),
                "score": round(score, 2)  # Recommendation score for display
            })

    return result


def get_similar_books(book_id, db, limit=6):
    """Get similar books using similarity matrix + content-based features"""
    book = db.books.find_one({"book_id": book_id})
    if not book:
        return []
    
    book_category = book.get("category")
    book_author = book.get("authors", "")
    book_author_main = book_author.split(",")[0].strip() if book_author else None
    
    similar_books = []
    scores = {}
    
    # Try to use similarity matrix first
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                similarity_df = pickle.load(f)
            
            if book_id in similarity_df.index:
                # Get books similar based on user ratings
                sim_scores = similarity_df[book_id].sort_values(ascending=False)[1:TOP_K+1]
                for similar_book_id, sim_value in sim_scores.items():
                    if sim_value > 0.1:  # Only use meaningful similarities
                        scores[similar_book_id] = scores.get(similar_book_id, 0) + sim_value
        except:
            pass  # Fallback to content-based if similarity matrix fails
    
    # CONTENT-BASED: Boost by category and author
    # Get books in same category
    if book_category:
        same_category = list(db.books.find({
            "category": book_category,
            "book_id": {"$ne": book_id}
        }))
        for b in same_category:
            bid = b["book_id"]
            # Category match gets high boost
            scores[bid] = scores.get(bid, 0) + 0.5
            # Extra boost if also has good rating
            if b.get("average_rating", 0) >= 4.0:
                scores[bid] = scores.get(bid, 0) + 0.2
    
    # Get books by same author (or similar authors)
    if book_author_main:
        same_author = list(db.books.find({
            "authors": {"$regex": book_author_main, "$options": "i"},
            "book_id": {"$ne": book_id}
        }).limit(3))  # Limit to avoid too many from same author
        for b in same_author:
            bid = b["book_id"]
            # Author match gets boost
            scores[bid] = scores.get(bid, 0) + 0.3
    
    # Combine both: If book has both category AND similarity, it scores higher
    # Sort by score and get top results
    sorted_books = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Get top similar books
    result_ids = [bid for bid, score in sorted_books[:limit]]
    
    # Fill with category matches if we don't have enough
    if len(result_ids) < limit and book_category:
        category_books = list(db.books.find({
            "category": book_category,
            "book_id": {"$nin": result_ids + [book_id]}
        }).sort("average_rating", -1).limit(limit - len(result_ids)))
        result_ids.extend([b["book_id"] for b in category_books])
    
    # Get full book details
    for bid in result_ids[:limit]:
        b = db.books.find_one({"book_id": bid})
        if b:
            similar_books.append(b)
    
    return similar_books
