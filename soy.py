"""SushiSocial - A social media application built with PyQt6."""

import sqlite3
import sys
from datetime import datetime
import requests

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget
)

# Theme colors
COLORS = {
    'bg_primary': "#320B35",
    'bg_secondary': "#979AAA",
    'accent': "#238636",
    'accent_hover': "#2ea043",
    'text_primary': "#ffffff",
    'text_secondary': "#8b949e",
    'border': "#30363d",
    'post_bg': "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #161b22, stop:1 #1f242d)",
    'light_gray': "#30363d",
    '2771814951420192011820':"#00008B",
    '27718149514205144' :"#320b35",
    '20524201297820' :"#4E5754",
    '2212020151427' :"#282828",
    '2212020151481522518' :"#CC6666"
}

class Profile:
    """User profile containing username, bio, and posts."""
    def __init__(self, username: str, bio: str = "") -> None:
        self.username = username
        self.bio = bio
        self.avatar = None
        self.posts = []

class Post:
    """Post containing title, content, and metadata."""
    def __init__(self, title: str, author: str, content: str = "") -> None:
        self.title = title
        self.author = author
        self.content = content
        self.comments = []
        self.likes = 0
        self.timestamp = datetime.now()

class LoginDialog(QDialog):
    """Dialog for user login and registration."""
    def __init__(self, db_path: str, parent=None) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        self.setModal(True)
        self.setup_ui()
    
    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        reply = QMessageBox.question(
            self, 'Exit', 
            'Do you want to exit?',
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)
        
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password")
        layout.addWidget(self.password)
        
        buttons = QHBoxLayout()
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        buttons.addWidget(login_btn)
        
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.handle_register)
        buttons.addWidget(register_btn)
        
        layout.addLayout(buttons)

    def handle_login(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (self.username.text(), self.password.text()))
        user = cur.fetchone()
        conn.close()
        
        if user:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")
            
    def handle_register(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (self.username.text(), self.password.text()))
            conn.commit()
            QMessageBox.information(self, "Success", "Registration successful!")
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Username already exists")
        finally:
            conn.close()

class SushiSocial(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_url = "http://localhost:8000"
        self.setWindowTitle("Sushi Social")
        self.setStyleSheet(f"background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']};")
        self.resize(1200, 800)
        
        self.db_path = "social.db"
        self.setup_database()
        self.current_user = None
        self.setup_ui()
        self.show_login_dialog()

    def setup_database(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        cur = conn.cursor()
        
        # Drop existing tables to fix schema
        cur.execute("DROP TABLE IF EXISTS posts")
        cur.execute("DROP TABLE IF EXISTS users")
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                bio TEXT DEFAULT '',
                avatar_path TEXT
            )
        """)
        
        # Create posts table with user_id instead of author
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                user_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                user_id INTEGER,
                post_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                post_id INTEGER,
                rating INTEGER CHECK(rating IN (1,2,3,4,5)),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (post_id) REFERENCES posts (id),
                UNIQUE(user_id, post_id)
            )
        """)
        
        # Add likes/dislikes tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_reactions (
                id INTEGER PRIMARY KEY,
                post_id INTEGER,
                user_id INTEGER,
                is_like BOOLEAN,
                FOREIGN KEY (post_id) REFERENCES posts (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(post_id, user_id)
            )
        """)
        conn.commit()
        conn.close()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Profile Panel
        profile_panel = QWidget()
        profile_layout = QVBoxLayout(profile_panel)
        
        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(150, 150)
        self.avatar_label.setStyleSheet("background-color: gray; border-radius: 75px;")
        profile_layout.addWidget(self.avatar_label)
        
        # Username
        self.username_label = QLabel("Guest")
        self.username_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        profile_layout.addWidget(self.username_label)
        
        # Bio
        self.bio_edit = QTextEdit()
        self.bio_edit.setPlaceholderText("Write about yourself...")
        self.bio_edit.setMaximumHeight(100)
        profile_layout.addWidget(self.bio_edit)
        
        # Change Avatar Button
        avatar_btn = QPushButton("Change Avatar")
        avatar_btn.clicked.connect(self.change_avatar)
        profile_layout.addWidget(avatar_btn)
        
        layout.addWidget(profile_panel)
        
        # Posts panel setup
        posts_panel = QWidget()
        posts_layout = QVBoxLayout(posts_panel)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.posts_widget = QWidget()
        self.posts_area = QVBoxLayout(self.posts_widget)
        scroll.setWidget(self.posts_widget)
        posts_layout.addWidget(scroll)
        
        new_post_btn = QPushButton("New Post")
        new_post_btn.clicked.connect(self.show_new_post_dialog)
        posts_layout.addWidget(new_post_btn)
        
        layout.addWidget(posts_panel)

    def change_avatar(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Avatar", "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if file_name:
            pixmap = QPixmap(file_name).scaled(
                150, 150, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.avatar_label.setPixmap(pixmap)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET avatar_path=? WHERE username=?",
                (file_name, self.current_user.username)
            )
            conn.commit()
            conn.close()

    def load_user_profile(self, username):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT bio, avatar_path FROM users WHERE username=?",
            (username,)
        )
        result = cur.fetchone()
        conn.close()
        
        if result:
            self.bio_edit.setText(result[0] or "")
            if result[1]:  # Avatar path
                pixmap = QPixmap(result[1]).scaled(
                    150, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.avatar_label.setPixmap(pixmap)

    def show_login_dialog(self):
        dialog = LoginDialog(self.db_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_user = Profile(dialog.username.text())
            self.username_label.setText(self.current_user.username)
            self.load_user_profile(self.current_user.username)
            self.load_posts()

    def create_post(self, title: str, content: str):
        try:
            response = requests.post(
                f"{self.api_url}/posts",
                params={
                    "title": title,
                    "content": content,
                    "username": self.current_user.username
                }
            )
            if response.status_code == 200:
                self.load_posts()
                return True
            return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create post: {e}")
            return False

    def load_posts(self):
        try:
            response = requests.get(f"{self.api_url}/posts")
            if response.status_code == 200:
                posts = response.json()
                self.update_posts_display(posts)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load posts: {e}")

    def show_new_post_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Post")
        dialog.setStyleSheet(f"""
            QDialog {{ 
                background: {COLORS["27718149514205144"]};
                border-radius: 10px;
                padding: 20px;
            }}
            QLineEdit, QTextEdit {{
                background: {COLORS['27718149514205144']};
                color: {COLORS['20524201297820']};
                border: 1px solid {COLORS['2212020151427']};
                border-radius: 5px;
                padding: 10px;
            }}
            QPushButton {{
                background: {COLORS['2212020151427']};
                color: {COLORS['20524201297820']};
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background: {COLORS['2212020151481522518']};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        
        title_input = QLineEdit()
        title_input.setPlaceholderText("Post Title")
        layout.addWidget(title_input)
        
        content_input = QTextEdit()
        content_input.setPlaceholderText("Write your post...")
        layout.addWidget(content_input)
        
        def create_post():
            if not title_input.text() or not content_input.toPlainText():
                QMessageBox.warning(dialog, "Error", "Title and content required")
                return
                
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            try:
                cur.execute("SELECT id FROM users WHERE username = ?", 
                           (self.current_user.username,))
                user_id = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO posts (title, content, user_id, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    title_input.text(),
                    content_input.toPlainText(),
                    user_id,
                    datetime.now()
                ))
                conn.commit()
                self.load_posts()
                dialog.accept()
            except sqlite3.Error as e:
                QMessageBox.critical(dialog, "Error", f"Failed to create post: {e}")
            finally:
                conn.close()
        
        post_btn = QPushButton("Post")
        post_btn.clicked.connect(create_post)
        layout.addWidget(post_btn)
        
        dialog.exec()

    def update_posts_display(self, posts):
        # Clear existing posts
        while self.posts_area.count():
            item = self.posts_area.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for post in posts:
            post_widget = QFrame()
            post_widget.setStyleSheet(f"background-color: {COLORS['light_gray']}; border-radius: 10px; padding: 10px;")
            post_layout = QVBoxLayout(post_widget)
            
            # Post header with title and author
            header_layout = QHBoxLayout()
            title_label = QLabel(post[0])
            title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            header_layout.addWidget(title_label)
            post_layout.addLayout(header_layout)
            
            # Rating stars
            rating_layout = QHBoxLayout()
            for i in range(5):
                star_btn = QPushButton("★")
                star_btn.setFixedSize(30, 30)
                star_btn.clicked.connect(lambda x, p=post[3], r=i+1: self.rate_post(p, r))
                rating_layout.addWidget(star_btn)
            post_layout.addLayout(rating_layout)
            
            # Content with preserved line breaks
            content_label = QLabel(post[1].replace('\n', '<br>'))
            content_label.setWordWrap(True)
            content_label.setTextFormat(Qt.TextFormat.RichText)
            post_layout.addWidget(content_label)
            
            # Reactions layout
            reactions = QHBoxLayout()
            
            like_count = self.get_reaction_count(post[3], True)
            dislike_count = self.get_reaction_count(post[3], False)
            
            like_btn = QPushButton(f"👍 {like_count}")
            like_btn.clicked.connect(lambda x, p=post[3]: self.handle_reaction(p, True))
            
            dislike_btn = QPushButton(f"👎 {dislike_count}")
            dislike_btn.clicked.connect(lambda x, p=post[3]: self.handle_reaction(p, False))
            
            reactions.addWidget(like_btn)
            reactions.addWidget(dislike_btn)
            post_layout.addLayout(reactions)
            
            # Comments section
            comments_widget = QWidget()
            comments_layout = QVBoxLayout(comments_widget)
            
            # Add comment
            comment_input = QLineEdit()
            comment_input.setPlaceholderText("Add a comment...")
            comment_btn = QPushButton("Comment")
            comment_btn.clicked.connect(
                lambda: self.add_comment(post[3], comment_input.text())
            )
            
            comments_layout.addWidget(comment_input)
            comments_layout.addWidget(comment_btn)
            
            # Show existing comments
            for comment in self.get_comments(post[3]):
                comment_label = QLabel(f"{comment[1]}: {comment[0]}")
                comments_layout.addWidget(comment_label)
                
            post_layout.addWidget(comments_widget)
            self.posts_area.addWidget(post_widget)

    def rate_post(self, post_id, rating):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR REPLACE INTO ratings (user_id, post_id, rating)
                VALUES ((SELECT id FROM users WHERE username = ?), ?, ?)
            """, (self.current_user.username, post_id, rating))
            conn.commit()
        finally:
            conn.close()
        self.load_posts()

    def handle_reaction(self, post_id, is_like):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            # Get user_id
            cur.execute("SELECT id FROM users WHERE username = ?", 
                       (self.current_user.username,))
            user_id = cur.fetchone()[0]
            
            # Toggle reaction
            cur.execute("""
                INSERT OR REPLACE INTO post_reactions (post_id, user_id, is_like)
                VALUES (?, ?, ?)
            """, (post_id, user_id, is_like))
            conn.commit()
        finally:
            conn.close()
        self.load_posts()

    def get_reaction_count(self, post_id, is_like):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM post_reactions 
            WHERE post_id = ? AND is_like = ?
        """, (post_id, is_like))
        count = cur.fetchone()[0]
        conn.close()
        return count

    def add_comment(self, post_id, content):
        if not content.strip():
            return
            
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO comments (content, user_id, post_id)
                VALUES (?, (SELECT id FROM users WHERE username = ?), ?)
            """, (content, self.current_user.username, post_id))
            conn.commit()
        finally:
            conn.close()
        self.load_posts()

    def get_comments(self, post_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT c.content, u.username 
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.timestamp DESC
        """, (post_id,))
        comments = cur.fetchall()
        conn.close()
        return comments

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SushiSocial()
    window.show()
    sys.exit(app.exec())