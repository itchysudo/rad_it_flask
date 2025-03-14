from flask_bcrypt import Bcrypt
import psycopg2

# Initialize bcrypt
bcrypt = Bcrypt()

# Database connection settings
DB_NAME = "RAD_IT"
DB_USER = "postgres"
DB_PASSWORD = "Gr33kG0d"  # Change this to your actual database password
DB_HOST = "localhost"

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST
)
cur = conn.cursor()

# Generate a hashed password
hashed_password = bcrypt.generate_password_hash("admin123").decode('utf-8')

# Insert into users table
cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", ("admin", hashed_password))

conn.commit()
cur.close()
conn.close()

print("✅ Admin user created successfully! You can now log in with username: admin and password: admin123.")
