"""
Performance Testing Script for GoodBooks Recommendation System

This script evaluates the performance of:
1. Database queries
2. Recommendation generation
3. Search functionality
4. API response times

Run with: python performance_test.py
"""

import time
import statistics
from pymongo import MongoClient
from recommend import get_recommendations, build_item_similarity
from models import search_books, get_book, get_user_interactions
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["goodbooks"]


def time_function(func, *args, **kwargs):
    """Measure execution time of a function"""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def test_database_queries(n=100):
    """Test database query performance"""
    print("\n" + "="*60)
    print("Testing Database Query Performance")
    print("="*60)
    
    times = []
    
    # Test: Find books
    print("\n1. Testing book queries...")
    for _ in range(n):
        _, elapsed = time_function(lambda: list(db.books.find().limit(10)))
        times.append(elapsed * 1000)  # Convert to ms
    
    print(f"   Average: {statistics.mean(times):.2f}ms")
    print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")
    print(f"   Median: {statistics.median(times):.2f}ms")
    
    # Test: Search by category
    times = []
    categories = get_all_categories(db)[:5] if hasattr(db.books, 'distinct') else []
    if categories:
        print("\n2. Testing category search...")
        for category in categories:
            for _ in range(n // len(categories)):
                _, elapsed = time_function(lambda c=category: list(db.books.find({"category": c}).limit(10)))
                times.append(elapsed * 1000)
        
        print(f"   Average: {statistics.mean(times):.2f}ms")
        print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")
    
    # Test: Get book by ID
    times = []
    book_ids = [b["book_id"] for b in db.books.find().limit(100)]
    print("\n3. Testing get book by ID...")
    for book_id in book_ids[:n]:
        _, elapsed = time_function(lambda bid=book_id: db.books.find_one({"book_id": bid}))
        times.append(elapsed * 1000)
    
    print(f"   Average: {statistics.mean(times):.2f}ms")
    print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")
    
    # Test: Text search
    times = []
    print("\n4. Testing text search...")
    search_terms = ["fiction", "mystery", "love", "science", "history"]
    for term in search_terms:
        for _ in range(n // len(search_terms)):
            _, elapsed = time_function(lambda t=term: search_books(db, t))
            times.append(elapsed * 1000)
    
    print(f"   Average: {statistics.mean(times):.2f}ms")
    print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")


def test_recommendation_performance():
    """Test recommendation generation performance"""
    print("\n" + "="*60)
    print("Testing Recommendation Generation Performance")
    print("="*60)
    
    # Get users with ratings
    users_with_ratings = db.interactions.distinct("user_id")[:20]
    
    if not users_with_ratings:
        print("\nNo users with ratings found. Skipping recommendation tests.")
        return
    
    print(f"\nTesting with {len(users_with_ratings)} users...")
    
    times = []
    rec_counts = []
    
    for user_id in users_with_ratings:
        try:
            _, elapsed = time_function(get_recommendations, user_id, db)
            recs = get_recommendations(user_id, db)
            times.append(elapsed * 1000)  # Convert to ms
            rec_counts.append(len(recs))
        except Exception as e:
            print(f"   Error with user {user_id}: {e}")
            continue
    
    if times:
        print(f"\n   Average generation time: {statistics.mean(times):.2f}ms")
        print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")
        print(f"   Median: {statistics.median(times):.2f}ms")
        print(f"\n   Average recommendations per user: {statistics.mean(rec_counts):.1f}")
        print(f"   Min: {min(rec_counts)}, Max: {max(rec_counts)}")
    else:
        print("\n   No successful recommendation generations.")


def test_similarity_build():
    """Test similarity matrix build performance"""
    print("\n" + "="*60)
    print("Testing Similarity Matrix Build Performance")
    print("="*60)
    
    rating_count = db.interactions.count_documents({"rating": {"$ne": None}})
    print(f"\nTotal ratings in database: {rating_count:,}")
    
    if rating_count < 10:
        print("Not enough ratings to build similarity matrix. Skipping.")
        return
    
    print("\nBuilding similarity matrix...")
    start = time.time()
    try:
        build_item_similarity(db, force_rebuild=True)
        elapsed = time.time() - start
        print(f"\n   Build time: {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
        
        # Check file size if exists
        cache_file = "data/sim_cache.pkl"
        if os.path.exists(cache_file):
            size_mb = os.path.getsize(cache_file) / (1024 * 1024)
            print(f"   Cache file size: {size_mb:.2f} MB")
    except Exception as e:
        print(f"\n   Error building similarity matrix: {e}")


def test_interaction_queries():
    """Test interaction query performance"""
    print("\n" + "="*60)
    print("Testing Interaction Query Performance")
    print("="*60)
    
    users_with_interactions = db.interactions.distinct("user_id")[:20]
    
    if not users_with_interactions:
        print("\nNo users with interactions found.")
        return
    
    print(f"\nTesting with {len(users_with_interactions)} users...")
    
    # Test: Get user interactions
    times = []
    for user_id in users_with_interactions:
        _, elapsed = time_function(lambda uid=user_id: list(db.interactions.find({"user_id": uid})))
        times.append(elapsed * 1000)
    
    if times:
        print(f"\n   Average query time: {statistics.mean(times):.2f}ms")
        print(f"   Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")


def get_database_stats():
    """Get database statistics"""
    print("\n" + "="*60)
    print("Database Statistics")
    print("="*60)
    
    try:
        book_count = db.books.count_documents({})
        user_count = db.users.count_documents({})
        interaction_count = db.interactions.count_documents({})
        rating_count = db.interactions.count_documents({"rating": {"$ne": None}})
        
        print(f"\n   Books: {book_count:,}")
        print(f"   Users: {user_count:,}")
        print(f"   Interactions: {interaction_count:,}")
        print(f"   Ratings: {rating_count:,}")
        
        # Get index info
        indexes = db.books.index_information()
        print(f"\n   Book Collection Indexes: {len(indexes)}")
        for index_name in indexes.keys():
            print(f"     - {index_name}")
            
    except Exception as e:
        print(f"\n   Error getting stats: {e}")


def optimize_database():
    """Suggest database optimizations"""
    print("\n" + "="*60)
    print("Database Optimization Suggestions")
    print("="*60)
    
    suggestions = []
    
    # Check indexes
    indexes = db.books.index_information()
    if "book_id_1" not in indexes:
        suggestions.append("Add index on 'book_id' for faster lookups")
    
    if "category_1" not in indexes:
        suggestions.append("Add index on 'category' for category filtering")
    
    interaction_indexes = db.interactions.index_information()
    if "user_id_1" not in interaction_indexes:
        suggestions.append("Add index on interactions.user_id")
    
    if "book_id_1" not in interaction_indexes:
        suggestions.append("Add index on interactions.book_id")
    
    if "user_id_1_book_id_1" not in interaction_indexes:
        suggestions.append("Add compound index on (user_id, book_id) for faster lookups")
    
    if suggestions:
        print("\n   Suggested optimizations:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"     {i}. {suggestion}")
    else:
        print("\n   Database appears to be well-optimized!")


def main():
    """Run all performance tests"""
    print("\n" + "="*60)
    print("GoodBooks Performance Test Suite")
    print("="*60)
    
    # Check database connection
    try:
        db.books.count_documents({})
        print("\n✓ Database connection successful")
    except Exception as e:
        print(f"\n✗ Database connection failed: {e}")
        return
    
    # Run tests
    get_database_stats()
    test_database_queries(n=50)  # Reduced for faster testing
    test_interaction_queries()
    test_recommendation_performance()
    test_similarity_build()
    optimize_database()
    
    print("\n" + "="*60)
    print("Performance Testing Complete")
    print("="*60)
    print("\nRecommendations:")
    print("  - Monitor query times in production")
    print("  - Consider caching frequently accessed data")
    print("  - Rebuild similarity matrix periodically")
    print("  - Use connection pooling for better performance")
    print("  - Consider pagination for large result sets\n")


if __name__ == "__main__":
    main()
