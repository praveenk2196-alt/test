import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

db = st.secrets["mysql"]

try:
    engine = create_engine(
               "mysql+pymysql://",
                   connect_args={
                       "host": "127.0.0.1",
                       "port": 3306,
                       "database": "tennis_game_analytics",
                       "user": "root",
                       "password": "1517"
                   }
               )
    

    with engine.connect() as connection:
        result = connection.execute(text("SELECT VERSION()"))
        st.success(f"MySQL connected! Version: {result.scalar()}")

except SQLAlchemyError as e:
    st.error(f"MySQL connection failed: {e}")
