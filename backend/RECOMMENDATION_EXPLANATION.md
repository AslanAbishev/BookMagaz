# Recommendation System Explanation

## How the Recommendation System Works

The GoodBooks recommendation system uses a **Hybrid Approach** combining:
1. **Item-Based Collaborative Filtering** (based on user ratings)
2. **Content-Based Filtering** (based on genre/category and author)

This provides better recommendations than using either method alone!

### 1. **Building the Similarity Matrix**

1. The system collects all user ratings from the database
2. Creates a user-item matrix where:
   - Rows = Users
   - Columns = Books
   - Values = Ratings (1-5 stars)
3. Computes cosine similarity between books:
   - Books that are rated similarly by users will have high similarity scores
   - Similarity ranges from -1 (completely opposite) to 1 (identical)

### 2. **Generating Recommendations (Hybrid Approach)**

When you visit your profile page, the system:

1. **Checks if you have ratings:**
   - If NO ratings → Shows popular books in your preferred categories (if any)
   - If YES ratings → Proceeds to personalized recommendations

2. **COLLABORATIVE FILTERING** (Primary method):
   - For each book you've rated:
     - Finds the 15 most similar books (based on how other users rated them)
     - Calculates score: `similarity_score × your_rating`
   - Aggregates scores from all your ratings
   - Books similar to multiple books you rated get higher scores

3. **CONTENT-BASED BOOST** (Genre/Category matching):
   - For books you rated 4+ stars:
     - Boosts books in the **same category/genre** (+30% boost)
     - Boosts books by the **same author** (+20% boost)
   - This ensures recommendations match your preferred genres

4. **Returns top 10 books:**
   - Sorted by combined recommendation score
   - Excludes books you've already rated
   - Combines both collaborative and content-based scores

### 3. **Example**

You rated:
- "Harry Potter" (Fantasy) by J.K. Rowling = 5 stars
- "The Hobbit" (Fantasy) by J.R.R. Tolkien = 4 stars

**Collaborative Filtering:**
- "Lord of the Rings" is 80% similar to "Harry Potter" → Score: 0.8 × 5 = 4.0
- "Lord of the Rings" is 90% similar to "The Hobbit" → Score: 0.9 × 4 = 3.6
- Collaborative score = 7.6

**Content-Based Boost:**
- "The Hobbit" is Fantasy + rated 4 stars → Genre boost
- Books in Fantasy category get +1.2 boost (0.3 × 4)
- Same author books get +0.8 boost (0.2 × 4)

**Final Score:**
- "Lord of the Rings" (Fantasy, same author as "The Hobbit")
  - Collaborative: 7.6
  - Genre boost: +1.2 (Fantasy match)
  - Author boost: +0.8 (Tolkien match)
  - **Total: 9.6** ⭐

"Lord of the Rings" appears high in your recommendations!

### 4. **Similar Books Feature**

On product pages, "Similar Books" uses:
1. **Collaborative similarity** (if available from ratings matrix)
2. **Same category/genre** matching (+0.5 boost)
3. **Same author** matching (+0.3 boost)
4. **High ratings** (+0.2 boost for 4+ star books)

Books that match multiple criteria score higher and appear first!

### 5. **Important Notes**

- **The similarity matrix must be rebuilt** after ratings are added to include them
- More ratings = better recommendations
- The system works best with multiple users rating multiple books
- Ratings from the CSV file (if loaded) are also used to build similarities

### 5. **Rebuilding the Similarity Matrix**

To rebuild the similarity matrix with new ratings:

1. Visit: `http://localhost:5000/admin/rebuild-sim`
2. Or use the API: `GET /admin/rebuild-sim`
3. This recalculates all book similarities based on current ratings

### 6. **Advantages of Hybrid Approach**

✅ **Better genre matching**: Recommends books in genres you like
✅ **Author discovery**: Finds other books by authors you enjoy
✅ **Collaborative insights**: Uses what similar users liked
✅ **Handles cold start**: Even new users get genre-based recommendations
✅ **More diverse**: Combines multiple signals for better recommendations

### 7. **Limitations**

- Cold start: New users with no ratings get popular books (but still filtered by category if available)
- Sparse data: If there aren't many ratings, content-based filtering fills the gaps
- Performance: Building the similarity matrix can be slow with many books/ratings
- Category quality: Recommendations depend on accurate category classification

## Technical Details

- **Algorithm**: Hybrid (Collaborative + Content-Based)
  - Collaborative: Item-based filtering with cosine similarity
  - Content-Based: Genre/category and author matching
- **Similarity Metric**: Cosine similarity for collaborative part
- **Boost Factors**:
  - Genre match: +30% of rating (for 4+ star books)
  - Author match: +20% of rating (for 4+ star books)
- **Matrix Size**: All books × All books (collaborative part)
- **Cache**: Similarity matrix is cached in `data/sim_cache.pkl`
- **Top K**: Uses top 15 most similar books per rated book
- **Similar Books**: Uses both similarity matrix + category/author matching

