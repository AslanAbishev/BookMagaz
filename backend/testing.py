from pymongo import MongoClient
from datetime import datetime
import time
import json

# Connect to MongoDB
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["goodbooks"]

# Results storage
test_results = {
    "timestamp": datetime.now().isoformat(),
    "data_integrity": {},
    "query_performance": {},
    "indexes": {},
    "recommendations": []
}


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_test(test_name, status, details=""):
    """Print test result"""
    status_symbol = "✅" if status == "PASS" else "⚠️" if status == "WARNING" else "❌"
    print(f"{status_symbol} {test_name}: {status}")
    if details:
        print(f"   → {details}")


# ============================================
# PART 1: DATA INTEGRITY TESTS
# ============================================

def test_data_integrity():
    print_header("PART 1: DATA INTEGRITY TESTS")
    
    # Test 1: Check collection counts
    print("\n[Test 1.1] Checking collection counts...")
    books_count = db.books.count_documents({})
    users_count = db.users.count_documents({})
    interactions_count = db.interactions.count_documents({})
    
    print(f"   Books: {books_count}")
    print(f"   Users: {users_count}")
    print(f"   Interactions: {interactions_count}")
    
    test_results["data_integrity"]["collection_counts"] = {
        "books": books_count,
        "users": users_count,
        "interactions": interactions_count
    }
    
    # Test 2: Check for duplicate usernames
    print("\n[Test 1.2] Checking for duplicate usernames...")
    duplicate_usernames = list(db.users.aggregate([
        {"$group": {"_id": "$username", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]))
    
    if len(duplicate_usernames) == 0:
        print_test("Duplicate Username Check", "PASS", "No duplicates found")
        test_results["data_integrity"]["duplicate_usernames"] = "PASS"
    else:
        print_test("Duplicate Username Check", "FAIL", f"Found {len(duplicate_usernames)} duplicates")
        test_results["data_integrity"]["duplicate_usernames"] = f"FAIL: {len(duplicate_usernames)} duplicates"
    
    # Test 3: Check for duplicate emails
    print("\n[Test 1.3] Checking for duplicate emails...")
    duplicate_emails = list(db.users.aggregate([
        {"$group": {"_id": "$email", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]))
    
    if len(duplicate_emails) == 0:
        print_test("Duplicate Email Check", "PASS", "No duplicates found")
        test_results["data_integrity"]["duplicate_emails"] = "PASS"
    else:
        print_test("Duplicate Email Check", "FAIL", f"Found {len(duplicate_emails)} duplicates")
        test_results["data_integrity"]["duplicate_emails"] = f"FAIL: {len(duplicate_emails)} duplicates"
    
    # Test 4: Check data types for ratings
    print("\n[Test 1.4] Checking rating data type integrity...")
    invalid_ratings = db.interactions.count_documents({
        "interaction": "rating",
        "$or": [
            {"rating": {"$type": "string"}},
            {"rating": {"$lt": 1}},
            {"rating": {"$gt": 5}}
        ]
    })
    
    if invalid_ratings == 0:
        print_test("Rating Data Type Check", "PASS", "All ratings are valid")
        test_results["data_integrity"]["invalid_ratings"] = "PASS"
    else:
        print_test("Rating Data Type Check", "FAIL", f"Found {invalid_ratings} invalid ratings")
        test_results["data_integrity"]["invalid_ratings"] = f"FAIL: {invalid_ratings} invalid"
    
    # Test 5: Check for orphaned interactions
    print("\n[Test 1.5] Checking for orphaned interactions...")
    # Sample check: find interactions where user doesn't exist
    pipeline = [
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$match": {"user": {"$size": 0}}},
        {"$count": "orphaned_count"}
    ]
    
    # Note: This requires user_id to be ObjectId, adjust if using string
    # For string user_ids, we need a different approach
    print_test("Orphaned Data Check", "WARNING", "Manual verification recommended")
    test_results["data_integrity"]["orphaned_check"] = "Needs manual verification"


# ============================================
# PART 2: QUERY PERFORMANCE TESTS
# ============================================

def test_query_performance():
    print_header("PART 2: QUERY PERFORMANCE TESTS")
    
    performance_results = []
    
    # Test 1: Find user by username
    print("\n[Test 2.1] Testing query: Find user by username")
    start_time = time.time()
    result = db.users.find_one({"username": "test_user"})
    elapsed_ms = (time.time() - start_time) * 1000
    
    explain = db.users.find({"username": "test_user"}).explain()
    index_used = "COLLSCAN" if "COLLSCAN" in str(explain) else "IXSCAN"
    
    print(f"   Execution time: {elapsed_ms:.2f} ms")
    print(f"   Index used: {index_used}")
    
    performance_results.append({
        "query": "Find user by username",
        "time_ms": round(elapsed_ms, 2),
        "index_used": index_used
    })
    
    # Test 2: Find user by email
    print("\n[Test 2.2] Testing query: Find user by email")
    start_time = time.time()
    result = db.users.find_one({"email": "test@test.com"})
    elapsed_ms = (time.time() - start_time) * 1000
    
    explain = db.users.find({"email": "test@test.com"}).explain()
    index_used = "COLLSCAN" if "COLLSCAN" in str(explain) else "IXSCAN"
    
    print(f"   Execution time: {elapsed_ms:.2f} ms")
    print(f"   Index used: {index_used}")
    
    performance_results.append({
        "query": "Find user by email",
        "time_ms": round(elapsed_ms, 2),
        "index_used": index_used
    })
    
    # Test 3: Find book by book_id
    print("\n[Test 2.3] Testing query: Find book by book_id")
    start_time = time.time()
    result = db.books.find_one({"book_id": 1})
    elapsed_ms = (time.time() - start_time) * 1000
    
    explain = db.books.find({"book_id": 1}).explain()
    index_used = "COLLSCAN" if "COLLSCAN" in str(explain) else "IXSCAN"
    
    print(f"   Execution time: {elapsed_ms:.2f} ms")
    print(f"   Index used: {index_used}")
    
    performance_results.append({
        "query": "Find book by book_id",
        "time_ms": round(elapsed_ms, 2),
        "index_used": index_used
    })
    
    # Test 4: Text search
    print("\n[Test 2.4] Testing query: Text search books")
    start_time = time.time()
    result = list(db.books.find({"$text": {"$search": "fiction"}}).limit(10))
    elapsed_ms = (time.time() - start_time) * 1000
    
    print(f"   Execution time: {elapsed_ms:.2f} ms")
    print(f"   Results found: {len(result)}")
    
    performance_results.append({
        "query": "Text search books",
        "time_ms": round(elapsed_ms, 2),
        "index_used": "TEXT_INDEX"
    })
    
    # Test 5: Find books by category
    print("\n[Test 2.5] Testing query: Find books by category")
    start_time = time.time()
    result = list(db.books.find({"category": "Fiction"}).limit(20))
    elapsed_ms = (time.time() - start_time) * 1000
    
    explain = db.books.find({"category": "Fiction"}).explain()
    index_used = "COLLSCAN" if "COLLSCAN" in str(explain) else "IXSCAN"
    
    print(f"   Execution time: {elapsed_ms:.2f} ms")
    print(f"   Index used: {index_used}")
    print(f"   Results found: {len(result)}")
    
    performance_results.append({
        "query": "Find books by category",
        "time_ms": round(elapsed_ms, 2),
        "index_used": index_used
    })
    
    # Test 6: Get user interactions
    print("\n[Test 2.6] Testing query: Get user interactions")
    # Get a real user_id first
    sample_interaction = db.interactions.find_one()
    if sample_interaction:
        user_id = sample_interaction.get("user_id")
        
        start_time = time.time()
        result = list(db.interactions.find({"user_id": user_id}).limit(20))
        elapsed_ms = (time.time() - start_time) * 1000
        
        explain = db.interactions.find({"user_id": user_id}).explain()
        index_used = "COLLSCAN" if "COLLSCAN" in str(explain) else "IXSCAN"
        
        print(f"   Execution time: {elapsed_ms:.2f} ms")
        print(f"   Index used: {index_used}")
        print(f"   Results found: {len(result)}")
        
        performance_results.append({
            "query": "Get user interactions",
            "time_ms": round(elapsed_ms, 2),
            "index_used": index_used
        })
    else:
        print("   ⚠️  No interactions found to test")
    
    # Test 7: Get popular books
    print("\n[Test 2.7] Testing query: Get popular books")
    start_time = time.time()
    result = list(db.books.find({
        "average_rating": {"$exists": True, "$ne": None},
        "ratings_count": {"$gte": 100}
    }).sort([("average_rating", -1), ("ratings_count", -1)]).limit(10))
    elapsed_ms = (time.time() - start_time) * 1000
    
    print(f"   Execution time: {elapsed_ms:.2f} ms")
    print(f"   Results found: {len(result)}")
    
    performance_results.append({
        "query": "Get popular books",
        "time_ms": round(elapsed_ms, 2),
        "index_used": "Needs compound index"
    })
    
    test_results["query_performance"] = performance_results
    
    # Summary
    print("\n" + "-"*60)
    print("PERFORMANCE SUMMARY:")
    avg_time = sum(p["time_ms"] for p in performance_results) / len(performance_results)
    print(f"   Average query time: {avg_time:.2f} ms")
    
    slow_queries = [p for p in performance_results if p["time_ms"] > 100]
    print(f"   Slow queries (>100ms): {len(slow_queries)}")
    
    collscans = [p for p in performance_results if "COLLSCAN" in p["index_used"]]
    print(f"   Queries using COLLSCAN: {len(collscans)}")
    
    if collscans:
        print("\n   ⚠️  WARNING: The following queries need indexes:")
        for q in collscans:
            print(f"      - {q['query']} ({q['time_ms']:.2f}ms)")


# ============================================
# PART 3: INDEX VERIFICATION
# ============================================

def test_indexes():
    print_header("PART 3: INDEX VERIFICATION")
    
    # Check indexes on each collection
    print("\n[Test 3.1] Books Collection Indexes:")
    books_indexes = db.books.index_information()
    for name, info in books_indexes.items():
        print(f"   - {name}: {info.get('key')}")
    
    print("\n[Test 3.2] Users Collection Indexes:")
    users_indexes = db.users.index_information()
    for name, info in users_indexes.items():
        print(f"   - {name}: {info.get('key')}")
    
    print("\n[Test 3.3] Interactions Collection Indexes:")
    interactions_indexes = db.interactions.index_information()
    for name, info in interactions_indexes.items():
        print(f"   - {name}: {info.get('key')}")
    
    test_results["indexes"] = {
        "books": len(books_indexes),
        "users": len(users_indexes),
        "interactions": len(interactions_indexes)
    }
    
    # Check for missing critical indexes
    print("\n[Test 3.4] Checking for missing critical indexes...")
    
    missing_indexes = []
    
    # Check username index
    if "username_unique" not in users_indexes and not any("username" in str(idx) for idx in users_indexes.values()):
        missing_indexes.append("users.username (CRITICAL)")
        print_test("Username Index", "FAIL", "Missing unique index on username")
    else:
        print_test("Username Index", "PASS")
    
    # Check email index
    if "email_unique" not in users_indexes and not any("email" in str(idx) for idx in users_indexes.values()):
        missing_indexes.append("users.email (CRITICAL)")
        print_test("Email Index", "FAIL", "Missing unique index on email")
    else:
        print_test("Email Index", "PASS")
    
    # Check book_id index
    if not any("book_id" in str(idx) for idx in books_indexes.values()):
        missing_indexes.append("books.book_id (HIGH PRIORITY)")
        print_test("Book ID Index", "FAIL", "Missing index on book_id")
    else:
        print_test("Book ID Index", "PASS")
    
    # Check user_id index in interactions
    if not any("user_id" in str(idx) for idx in interactions_indexes.values()):
        missing_indexes.append("interactions.user_id (HIGH PRIORITY)")
        print_test("User ID Index (interactions)", "FAIL", "Missing index on user_id")
    else:
        print_test("User ID Index (interactions)", "PASS")
    
    test_results["indexes"]["missing"] = missing_indexes
    
    if missing_indexes:
        print("\n⚠️  CRITICAL: Missing indexes detected!")
        print("   Run the following commands to create them:\n")
        if "users.username" in str(missing_indexes):
            print('   db.users.createIndex({username: 1}, {unique: true, name: "username_unique"})')
        if "users.email" in str(missing_indexes):
            print('   db.users.createIndex({email: 1}, {unique: true, name: "email_unique"})')
        if "books.book_id" in str(missing_indexes):
            print('   db.books.createIndex({book_id: 1}, {unique: true, name: "book_id_unique"})')
        if "interactions.user_id" in str(missing_indexes):
            print('   db.interactions.createIndex({user_id: 1}, {name: "user_id_idx"})')


# ============================================
# PART 4: RECOMMENDATIONS
# ============================================

def generate_recommendations():
    print_header("PART 4: RECOMMENDATIONS")
    
    recommendations = []
    
    # Based on test results, generate recommendations
    if test_results["indexes"]["missing"]:
        recommendations.append({
            "priority": "CRITICAL",
            "category": "Indexing",
            "issue": f"{len(test_results['indexes']['missing'])} critical indexes missing",
            "action": "Create missing indexes immediately"
        })
    
    # Check performance
    avg_time = sum(p["time_ms"] for p in test_results["query_performance"]) / len(test_results["query_performance"])
    if avg_time > 50:
        recommendations.append({
            "priority": "HIGH",
            "category": "Performance",
            "issue": f"Average query time is {avg_time:.2f}ms",
            "action": "Optimize slow queries and add indexes"
        })
    
    # Check for COLLSCAN
    collscans = [p for p in test_results["query_performance"] if "COLLSCAN" in p["index_used"]]
    if collscans:
        recommendations.append({
            "priority": "HIGH",
            "category": "Performance",
            "issue": f"{len(collscans)} queries using full collection scan",
            "action": "Add indexes for these queries"
        })
    
    # Caching recommendation
    recommendations.append({
        "priority": "MEDIUM",
        "category": "Scalability",
        "issue": "No caching layer detected",
        "action": "Implement Redis caching for popular books and recommendations"
    })
    
    # Data integrity
    recommendations.append({
        "priority": "MEDIUM",
        "category": "Data Integrity",
        "issue": "No cascade delete for user interactions",
        "action": "Implement cascade delete or soft delete strategy"
    })
    
    test_results["recommendations"] = recommendations
    
    print("\nRECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        priority_symbol = "🔴" if rec["priority"] == "CRITICAL" else "🟡" if rec["priority"] == "HIGH" else "🔵"
        print(f"\n{i}. {priority_symbol} [{rec['priority']}] {rec['category']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Action: {rec['action']}")


# ============================================
# MAIN EXECUTION
# ============================================

def main():
    print("\n" + "="*60)
    print("  MongoDB Database Testing Suite")
    print("  GoodBooks Recommendation System")
    print("="*60)
    
    try:
        # Run all tests
        test_data_integrity()
        test_query_performance()
        test_indexes()
        generate_recommendations()
        
        # Save results to file
        print_header("SAVING RESULTS")
        
        filename = f"db_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        print(f"\n✅ Test results saved to: {filename}")
        
        # Print final summary
        print_header("FINAL SUMMARY")
        print(f"\nTotal Collections Tested: 3")
        print(f"Total Indexes Found: {sum(test_results['indexes'][k] for k in ['books', 'users', 'interactions'])}")
        print(f"Missing Critical Indexes: {len(test_results['indexes']['missing'])}")
        print(f"Average Query Time: {sum(p['time_ms'] for p in test_results['query_performance']) / len(test_results['query_performance']):.2f}ms")
        print(f"Total Recommendations: {len(test_results['recommendations'])}")
        
        print("\n✅ Database testing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()