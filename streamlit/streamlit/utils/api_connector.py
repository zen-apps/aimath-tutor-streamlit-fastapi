import requests
import os
import streamlit as st
import json


# step 1
@st.cache_data()
def getting_key_math_concepts(question: str, user_dict: dict) -> dict:
    """Chat with the AI."""
    BACKEND_HOST = os.getenv("BACKEND_HOST")
    api_path = "v1/genai/ai_chat_get_key_concepts/"
    api_url = f"{BACKEND_HOST}{api_path}"

    query = {
        "question": json.dumps(question),
        "user_dict": json.dumps(user_dict),
    }
    response = requests.post(
        api_url, json=query, headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        raise ValueError(f"Error: {response.status_code}")
    return response.json()


# step 2
def ai_chat_agent_get_question(
    question_history: str, user_dict: dict, math_info: dict
) -> dict:
    """Get a math word problem question based on Grade, Topic."""
    BACKEND_HOST = os.getenv("BACKEND_HOST")
    api_path = "v1/genai/ai_chat_agent_get_question/"
    api_url = f"{BACKEND_HOST}{api_path}"

    query = {
        "question_history": json.dumps(question_history),
        "user_dict": json.dumps(user_dict),
        "math_info": json.dumps(math_info),
    }
    response = requests.post(
        api_url, json=query, headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        raise ValueError(f"Error: {response.status_code}")
    return response.json()
