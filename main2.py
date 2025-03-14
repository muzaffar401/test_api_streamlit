import os
import random
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Database setup
DATABASE_URL = "sqlite:///library.db"
class Base(DeclarativeBase):
    pass

class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, unique=True, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    genre = Column(String, nullable=False)
    read = Column(Boolean, default=False)
    issued = Column(Boolean, default=False)
    image_path = Column(String, nullable=True)

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

SessionLocal = init_db()

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def add_book(title, author, year, genre, read, image):
    session = SessionLocal()
    image_path = None
    if image is not None:
        image_folder = "book_images"
        ensure_dir(image_folder)
        image_path = os.path.join(image_folder, image.name)
        with open(image_path, "wb") as f:
            f.write(image.read())
    new_book = Book(title=title, author=author, year=year, genre=genre, read=read, issued=False, image_path=image_path)
    session.add(new_book)
    session.commit()
    session.close()

def remove_book(book_id):
    session = SessionLocal()
    book = session.query(Book).filter(Book.id == book_id).first()
    if book:
        session.delete(book)
        session.commit()
    session.close()

def get_all_books():
    session = SessionLocal()
    books = session.query(Book).all()
    session.close()
    return books

def update_book_status(book_id, issued):
    session = SessionLocal()
    book = session.query(Book).filter(Book.id == book_id).first()
    if book:
        book.issued = issued
        session.commit()
    session.close()

# def fetch_books_api(query):
#     url = f"https://www.googleapis.com/books/v1/volumes?q={query}&country=US"
#     response = requests.get(url)
#     if response.status_code == 200:
#         data = response.json()
#         return data.get("items", [])
#     st.warning("⚠ API call failed!")
#     return []
def fetch_books_api(query):
    # Get API key from Streamlit secrets
    api_key = st.secrets["books_api"]
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}"
    
    try:
        response = requests.get(url, timeout=10)  # 10-second timeout
        
        if response.status_code == 200:
            data = response.json()
            return data.get("items", [])

        elif response.status_code == 403:
            st.error("❌ API access forbidden. Check your API key and quota limits.")
        elif response.status_code == 429:
            st.warning("⚠ Too many requests! Google API rate limit exceeded. Try again later.")
        else:
            st.error(f"❌ API returned unexpected error: {response.status_code}")

    except requests.exceptions.Timeout:
        st.error("⚠ API request timed out! Please try again.")
    except requests.exceptions.ConnectionError:
        st.error("❌ Connection error! Check your internet connection.")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")

    return []


# Streamlit UI
st.set_page_config(page_title="📚 Library Manager", layout="wide")
st.title("📚 Personal Library Manager")
menu = ["Home", "Add Book", "Manage Books", "Statistics", "Recommendations", "API Search"]
choice = st.sidebar.radio("📌 Menu", menu)

if choice == "Home":
    # st.header("📖 Welcome to Your Personal Library Manager!")
    st.write("Manage your books, track what you've read, and get recommendations.")
    # st.image("https://source.unsplash.com/800x400/?books,library", use_container_width=True)
    image_url = "./library.jpg"

    try:
        st.image(image_url, use_container_width=True)
    except Exception as e:
        st.warning("📷 Image failed to load. Displaying a placeholder.")
        st.image("placeholder.jpg", use_container_width=True)  # Ensure you have a local placeholder image

elif choice == "Add Book":
    st.subheader("➕ Add a New Book")
    title = st.text_input("Title")
    author = st.text_input("Author")
    year = st.number_input("Publication Year", min_value=0, max_value=2025, step=1)
    genre = st.text_input("Genre")
    read = st.checkbox("Mark as Read")
    image = st.file_uploader("Upload Book Cover", type=["jpg", "jpeg", "png"])
    if st.button("Add Book", use_container_width=True):
        add_book(title, author, year, genre, read, image)
        st.success(f"📚 Added '{title}' to the library!")

elif choice == "Manage Books":
    st.subheader("📑 Manage Your Books")
    books = get_all_books()
    if books:
        df = pd.DataFrame([(book.id, book.title, book.author, book.year, book.genre, 'Read' if book.read else 'Unread', 'Issued' if book.issued else 'Available') for book in books], columns=["ID", "Title", "Author", "Year", "Genre", "Status", "Issued"])
        st.dataframe(df, use_container_width=True)
        book_id = st.number_input("Enter Book ID to Remove", min_value=1, step=1)
        if st.button("Remove Book", use_container_width=True):
            remove_book(book_id)
            st.success("🗑️ Book removed successfully!")

elif choice == "Statistics":
    st.subheader("📊 Library Statistics")
    books = get_all_books()
    total_books = len(books)
    read_books = sum(book.read for book in books)
    read_percentage = (read_books / total_books) * 100 if total_books > 0 else 0
    st.metric(label="Total Books", value=total_books)
    st.metric(label="Books Read", value=f"{read_books} ({read_percentage:.2f}%)")
    
    if total_books > 0:
        genre_counts = pd.Series([book.genre for book in books]).value_counts()
        st.bar_chart(genre_counts)
    else:
        st.warning("No books in the library. Add books to see genre distribution.")

elif choice == "Recommendations":
    st.subheader("🔍 Book Recommendations")
    unread_books = [book for book in get_all_books() if not book.read]
    if unread_books:
        recommended_book = random.choice(unread_books)
        st.write(f"📖 We recommend you read '{recommended_book.title}' by {recommended_book.author} ({recommended_book.year}) - {recommended_book.genre}")
    else:
        st.info("🎉 You've read all the books in your library!")

# elif choice == "API Search":
#     st.subheader("🌍 Search Books from API")
#     query = st.text_input("Search Books")
#     if st.button("Search API", use_container_width=True):
#         books = fetch_books_api(query)
#         if books:
#             for book in books:
#                 info = book.get("volumeInfo", {})
#                 title = info.get("title", "Unknown")
#                 author = ", ".join(info.get("authors", ["Unknown"]))
#                 book_link = info.get("infoLink", "#")
#                 st.write(f"**[{title}]({book_link})** by {author}")
#         else:
#             st.warning("No books found.")
st.subheader("🌍 Search Books from API")
query = st.text_input("Search Books")

if st.button("Search API", use_container_width=True):
    books = fetch_books_api(query)

    if books:
        for book in books:
            info = book.get("volumeInfo", {})
            title = info.get("title", "Unknown")
            author = ", ".join(info.get("authors", ["Unknown"]))
            book_link = info.get("infoLink", "#")
            thumbnail = info.get("imageLinks", {}).get("thumbnail", None)

            # Display the book title as a clickable link
            st.markdown(f"### [{title}]({book_link}) by {author}")

            # Display the book cover image if available
            if thumbnail:
                st.image(thumbnail, width=150)

            # Display book description if available
            description = info.get("description", "No description available.")
            st.write(description)

            st.markdown("---")  # Add a separator for better readability

    else:
        st.warning("No books found. Try another search term.")


st.sidebar.info("📚 Library Manager - Organize, Track, and Enjoy Your Books!")
