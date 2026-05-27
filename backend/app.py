from flask import Flask, render_template, request, jsonify, redirect, session, flash
from flask import url_for
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from recommend import get_recommendations, get_similar_books
from neural_recommend import (
    analyze_user_preferences,
    build_neural_recommender,
    get_neural_model_card,
    get_neural_recommendations,
    get_neural_status,
)
from models import (
    get_user_by_username, create_user, insert_interaction, get_book, search_books,
    get_user_interactions, get_user_purchase_history, get_user_ratings,
    get_all_categories, get_books_by_category, get_popular_books,
    check_user_interaction, get_user_by_id, update_user_profile,
    get_user_by_email, set_password_reset_token, get_user_by_reset_token,
    update_user_password
)
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from urllib.parse import quote

app = Flask(__name__, template_folder="templates", static_folder="../static")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey-change-in-production")

# DB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["goodbooks"]
# MongoDB collections
books_collection = db["books"]
ratings_collection = db["ratings"]
interactions_collection = db["interactions"]
users_collection = db["users"]


# --------------------------
# ROUTES
# --------------------------

@app.route("/")
def index():
    books = list(db.books.find().sort("average_rating", -1).limit(30))
    categories = get_all_categories(db)[:10]  # Top 10 categories for nav
    popular_books = get_popular_books(db, limit=6)
    
    # Get user's liked books if logged in
    user_likes = []
    if "user_id" in session:
        likes = get_user_interactions(db, session["user_id"], "like")
        user_likes = [like["book_id"] for like in likes]
    
    return render_template("index.html", 
                         books=books, 
                         categories=categories,
                         popular_books=popular_books,
                         user_likes=user_likes)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    email = request.form.get("email", "").strip()
    name = request.form.get("name", "").strip()

    # Validation
    if not username or not password:
        flash("Username and password are required", "error")
        return render_template("register.html")
    
    if not email:
        flash("Email is required", "error")
        return render_template("register.html")
    
    # Basic email validation
    if "@" not in email or "." not in email.split("@")[1]:
        flash("Please enter a valid email address", "error")
        return render_template("register.html")

    # Check for existing username
    existing_username = get_user_by_username(db, username)
    if existing_username:
        flash("Username already exists", "error")
        return render_template("register.html")
    
    # Check for existing email
    existing_email = get_user_by_email(db, email)
    if existing_email:
        flash("Email address is already registered", "error")
        return render_template("register.html")
    
    # Password validation
    if len(password) < 6:
        flash("Password must be at least 6 characters long", "error")
        return render_template("register.html")

    hashed = generate_password_hash(password)
    create_user(db, username, hashed, email=email, name=name)
    flash("Registration successful! Please login.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_username(db, username)
    if not user:
        flash("Invalid username or password", "error")
        return render_template("login.html")

    if not check_password_hash(user["password"], password):
        flash("Invalid username or password", "error")
        return render_template("login.html")

    session["user_id"] = str(user["_id"])
    session["username"] = user["username"]

    # Track login interaction
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password - request password reset"""
    if request.method == "GET":
        return render_template("forgot_password.html")
    
    email = request.form.get("email", "").strip()
    
    if not email:
        flash("Email is required", "error")
        return render_template("forgot_password.html")
    
    user = get_user_by_email(db, email)
    
    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=24)  # Token valid for 24 hours
        
        # Save token to database
        set_password_reset_token(db, email, reset_token, expiry)
        
        # In a production app, send email here
        # For now, we'll show the reset link (for development only)
        reset_url = url_for("reset_password", token=reset_token, _external=True)
        
        flash(f"Password reset link generated! (Development mode: {reset_url})", "info")
        # In production, send email:
        # send_password_reset_email(user.email, reset_url)
        # flash("Password reset link has been sent to your email", "success")
    else:
        # Don't reveal if email exists for security
        flash("If an account exists with that email, a password reset link has been sent.", "info")
    
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password using token"""
    user = get_user_by_reset_token(db, token)
    
    if not user:
        flash("Invalid or expired password reset token", "error")
        return redirect(url_for("forgot_password"))
    
    if request.method == "GET":
        return render_template("reset_password.html", token=token)
    
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    
    if not password:
        flash("Password is required", "error")
        return render_template("reset_password.html", token=token)
    
    if len(password) < 6:
        flash("Password must be at least 6 characters long", "error")
        return render_template("reset_password.html", token=token)
    
    if password != confirm_password:
        flash("Passwords do not match", "error")
        return render_template("reset_password.html", token=token)
    
    # Update password
    hashed = generate_password_hash(password)
    update_user_password(db, user["_id"], hashed)
    
    flash("Password reset successful! Please login with your new password.", "success")
    return redirect(url_for("login"))


@app.route("/product/<int:book_id>")
def product(book_id):
    book = get_book(db, book_id)
    if not book:
        flash("Book not found", "error")
        return redirect(url_for("index"))
    
    # Track view if user is logged in
    if "user_id" in session:
        # Check if already viewed recently (avoid duplicate views)
        recent_view = check_user_interaction(db, session["user_id"], book_id, "view")
        if not recent_view:
            insert_interaction(db, session["user_id"], book_id, "view")
    
    # Get user's interaction status
    user_rating = None
    user_liked = False
    if "user_id" in session:
        rating_obj = check_user_interaction(db, session["user_id"], book_id, "rating")
        if rating_obj and rating_obj.get("rating"):
            user_rating = rating_obj["rating"]
        user_liked = check_user_interaction(db, session["user_id"], book_id, "like") is not None
    
    # Get similar books using enhanced similarity algorithm
    similar_books = get_similar_books(book_id, db, limit=6)
    
    return render_template("product.html", 
                         book=book, 
                         user_rating=user_rating,
                         user_liked=user_liked,
                         similar_books=similar_books)


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(db, user_id)
    
    if not user:
        session.clear()
        return redirect(url_for("login"))

    recs = get_neural_recommendations(user_id, db, limit=10, include_model_info=True)
    purchase_history = get_user_purchase_history(db, user_id)
    ratings = get_user_ratings(db, user_id)
    likes = get_user_interactions(db, user_id, "like")
    
    # Get book details for history
    history_books = []
    for purchase in purchase_history[:10]:  # Last 10 purchases
        book = get_book(db, purchase["book_id"])
        if book:
            history_books.append({
                "book": book,
                "purchased_at": purchase.get("timestamp")
            })
    
    # Get book details for ratings
    rating_books = []
    for rating in ratings[:10]:  # Last 10 ratings
        book = get_book(db, rating["book_id"])
        if book:
            rating_books.append({
                "book": book,
                "rating": rating.get("rating"),
                "rated_at": rating.get("timestamp")
            })
    
    # Neural recommendations already include book details, scores, reasons, and model metadata.
    rec_books = []
    for rec in recs:
        if rec.get("title") and rec.get("authors"):
            rec_books.append(rec)
        elif rec.get("book_id"):
            book = get_book(db, rec.get("book_id"))
            if book:
                book["score"] = rec.get("score")
                book["neural_score"] = rec.get("neural_score")
                book["reason"] = rec.get("reason")
                book["score_components"] = rec.get("score_components")
                book["model_info"] = rec.get("model_info")
                rec_books.append(book)
        elif rec.get("title"):  # Fallback if only title/author in rec
            rec_books.append(rec)
    
    return render_template("profile.html", 
                         user=user,
                         recs=rec_books,
                         history_books=history_books,
                         rating_books=rating_books,
                         likes=likes)


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    user = get_user_by_id(db, user_id)
    
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        name = request.form.get("name", "").strip()
        update_user_profile(db, user_id, email=email, name=name)
        flash("Profile updated successfully", "success")
        return redirect(url_for("profile"))
    
    return render_template("edit_profile.html", user=user)


@app.route("/category/<category_name>")
def category_page(category_name):
    books = get_books_by_category(db, category_name, limit=50)
    return render_template("category.html", category=category_name, books=books)


@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    purchases = get_user_purchase_history(db, user_id)
    
    history_items = []
    for purchase in purchases:
        book = get_book(db, purchase["book_id"])
        if book:
            history_items.append({
                "book": book,
                "purchased_at": purchase.get("timestamp")
            })
    
    return render_template("history.html", history_items=history_items)


# --------------------------
# API ENDPOINTS
# --------------------------

@app.post("/api/interact")
def api_interact():
    """API endpoint for user interactions (view, like, purchase, rating)"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session["user_id"]
    book_id = data.get("book_id")
    interaction = data.get("interaction", "view")
    rating = data.get("rating", None)

    if not book_id:
        return jsonify({"error": "book_id required"}), 400

    insert_interaction(db, user_id, book_id, interaction, rating)
    return jsonify({"status": "ok", "message": f"{interaction} recorded"})


@app.post("/api/rate")
def api_rate():
    """Rate a book"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session["user_id"]
    book_id = data.get("book_id")
    rating = data.get("rating")

    if not book_id or not rating:
        return jsonify({"error": "book_id and rating required"}), 400

    try:
        rating = float(rating)
        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
    except:
        return jsonify({"error": "Invalid rating"}), 400

    # Check if user already rated this book, update instead of creating duplicate
    existing = db.interactions.find_one({
        "user_id": str(user_id),
        "book_id": int(book_id),
        "interaction": "rating"
    })
    
    if existing:
        # Update existing rating
        db.interactions.update_one(
            {"_id": existing["_id"]},
            {"$set": {"rating": rating, "timestamp": datetime.utcnow()}}
        )
    else:
        # Create new rating
        insert_interaction(db, user_id, book_id, "rating", rating)
    
    return jsonify({"status": "ok", "message": "Rating saved", "note": "Rebuild similarity matrix to update recommendations"})


@app.post("/api/like")
def api_like():
    """Like or unlike a book"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session["user_id"]
    book_id = data.get("book_id")
    action = data.get("action", "like")  # 'like' or 'unlike'

    if not book_id:
        return jsonify({"error": "book_id required"}), 400

    if action == "unlike":
        db.interactions.delete_one({
            "user_id": user_id,
            "book_id": int(book_id),
            "interaction": "like"
        })
        return jsonify({"status": "ok", "message": "Unliked"})
    else:
        # Check if already liked
        if not check_user_interaction(db, user_id, book_id, "like"):
            insert_interaction(db, user_id, book_id, "like")
        return jsonify({"status": "ok", "message": "Liked"})


@app.post("/api/purchase")
def api_purchase():
    """Record a purchase"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session["user_id"]
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id required"}), 400

    insert_interaction(db, user_id, book_id, "purchase")
    return jsonify({"status": "ok", "message": "Purchase recorded"})


@app.get("/api/search")
def api_search():
    """Search books by text and optionally category"""
    q = request.args.get("q", "").strip()
    category = request.args.get("category", None)
    if category and category.strip() == "":
        category = None
    limit = int(request.args.get("limit", 50))
    
    try:
        books = search_books(db, q, category=category, limit=limit)
        print(f"DEBUG: Search query='{q}', category={category}, found {len(books)} books")
        
        result = [{
            "book_id": b.get("book_id"),
            "title": b.get("title", ""),
            "authors": b.get("authors", ""),
            "category": b.get("category", ""),
            "average_rating": b.get("average_rating"),
            "price": b.get("price", 0),
            "image_url": b.get("image_url", "")
        } for b in books]
        
        print(f"DEBUG: Returning {len(result)} results")
        return jsonify(result)
    except Exception as e:
        # Log error for debugging
        import traceback
        print(f"Search error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.get("/api/recommend/<user_id>")
def api_recommend(user_id):
    """Get recommendations for a user"""
    recs = get_recommendations(user_id, db)
    return jsonify(recs)


@app.get("/api/neural/recommend/<user_id>")
def api_neural_recommend(user_id):
    """Get neural/NLP hybrid recommendations for a user."""
    limit = int(request.args.get("limit", 10))
    include_model_info = request.args.get("debug", "").lower() in {"1", "true", "yes"}
    recs = get_neural_recommendations(user_id, db, limit=limit, include_model_info=include_model_info)
    return jsonify(recs)


@app.get("/api/neural/preferences/<user_id>")
def api_neural_preferences(user_id):
    """Analyze the user's preference profile from stored interactions."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if str(session["user_id"]) != str(user_id):
        return jsonify({"error": "Forbidden"}), 403

    return jsonify(analyze_user_preferences(user_id, db))


@app.get("/api/neural/model-card")
def api_neural_model_card():
    """Return architecture, training, and evaluation metadata for the neural model."""
    return jsonify(get_neural_model_card(db))


@app.get("/api/neural/status")
def api_neural_status():
    """Return the exact model artifacts currently loaded by the Flask app."""
    return jsonify(get_neural_status(db))


@app.get("/api/categories")
def api_categories():
    """Get all categories"""
    categories = get_all_categories(db)
    return jsonify(categories)


@app.get("/api/user/interactions")
def api_user_interactions():
    """Get user's interactions"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session["user_id"]
    interaction_type = request.args.get("type", None)
    interactions = get_user_interactions(db, user_id, interaction_type)
    
    # Convert ObjectId to string for JSON serialization
    for i in interactions:
        i["_id"] = str(i["_id"])
        if "timestamp" in i:
            i["timestamp"] = i["timestamp"].isoformat()
    
    return jsonify(interactions)

@app.route("/api/books", methods=["GET"])
def api_books():
    try:
        books_cursor = books_collection.find({}, {"_id": 0})
        books = list(books_cursor)
        return jsonify(books), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# --------------------------
# ADMIN: REBUILD SIMILARITY
# --------------------------

@app.get("/admin/rebuild-sim")
def admin_rebuild_sim():
    """Rebuild the similarity matrix with current ratings"""
    from recommend import build_item_similarity
    try:
        build_item_similarity(db, force_rebuild=True)
        rating_count = db.interactions.count_documents({"rating": {"$ne": None}})
        return f"Similarity matrix rebuilt successfully!<br>Using {rating_count} ratings from the database."
    except Exception as e:
        return f"Error rebuilding similarity matrix: {str(e)}"


@app.get("/admin/rebuild-neural")
def admin_rebuild_neural():
    """Rebuild neural user/book embeddings and NLP book embeddings."""
    try:
        epochs = int(request.args.get("epochs", 20))
        max_events = int(request.args.get("max_events", 5000))
        batch_size = int(request.args.get("batch_size", 2048))
        summary = build_neural_recommender(
            db,
            force_rebuild=True,
            epochs=epochs,
            max_training_events=max_events,
            batch_size=batch_size,
        )
        return (
            "Neural recommender rebuilt successfully!<br>"
            f"Epochs: {summary['epochs']}<br>"
            f"Max training events: {summary['max_training_events']}<br>"
            f"Batch size: {summary['batch_size']}<br>"
            f"Book text embeddings: {summary['book_embeddings']}<br>"
            f"Latent users: {summary['latent_users']}<br>"
            f"Latent books: {summary['latent_books']}<br>"
            f"Training events: {summary['training_events']}<br>"
            f"Validation RMSE: {summary['validation_rmse']}<br>"
            f"Validation MAE: {summary['validation_mae']}<br>"
            f"NLP method: {summary['text_embedding_method']}"
        )
    except Exception as e:
        return f"Error rebuilding neural recommender: {str(e)}", 500


if __name__ == "__main__":
    app.run(debug=True)
