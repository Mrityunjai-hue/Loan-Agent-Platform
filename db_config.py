import os
import psycopg2
import sys

def get_database_url():
    # 1. Try Environment Variable (GitHub Actions)
    url = os.environ.get('DATABASE_URL')
    if url:
        return url
    
    # 2. Try Streamlit Secrets (Streamlit Cloud)
    try:
        import streamlit as st
        # Check Streamlit secrets
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except:
        pass
        
    return None

def get_connection():
    url = get_database_url()
    if not url:
        return None
    try:
        return psycopg2.connect(url, sslmode='require')
    except Exception as e:
        return None
