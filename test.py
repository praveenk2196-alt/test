import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# App title
st.title("Tennis Player Dashboard")

# Database connection settings
# Change these to match your local MySQL setup
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "tennis_game_analytics"
DB_USER = "root"
DB_PASSWORD = "1517"

# Create database connection
url = URL.create(
    "mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

engine = create_engine(url)

# Read data from MySQL
try:
    with engine.connect() as connection:
        query ="""
             SELECT
             c.competitor_id,
                 c.name,
                 c.country,
                 c.country_code,
                 c.abbreviation,
                 cr.`rank`,
                 cr.movement,
                 cr.points,
                 cr.competitions_played
             FROM competitors c
             JOIN competitor_rankings cr
                 ON c.competitor_id = cr.competitor_id
             """
    
        df = pd.read_sql(query, connection)

    st.success("Database connected successfully!")

    # Display data
    st.subheader("Player Details")
    st.dataframe(df, use_container_width=True)

    # Show number of players
    st.metric("Total Players", len(df))

except Exception as e:
    st.error("Could not connect to the database.")
    st.caption(f"Error details: {e}")

finally:
    engine.dispose()
