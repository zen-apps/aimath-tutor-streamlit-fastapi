import streamlit as st
import json
import os

from utils.api_connector import (
    getting_key_math_concepts,
)


def run_llm_api_get_key_concepts(user_dict: dict):
    """Run the LLM API chat."""
    prompt = "not used"
    llm_response = getting_key_math_concepts(question=prompt, user_dict=user_dict)
    grade = user_dict["grade"]
    resp_dict = json.loads(llm_response["output"])

    concept_radio = st.radio(
        f"Select Concept for grade {grade}",
        [concept["concept_name"] for concept in resp_dict],
    )
    concept_dict = {}
    for concept in resp_dict:
        if concept_radio == concept["concept_name"]:
            concept_dict = concept
            concept_dict["grade"] = grade
            break
    st.write(f":orange[{concept_dict['concept_description']}]")
    st.session_state["concept_dict"] = concept_dict

    st.session_state["user_dict"] = user_dict

    provide_question_button = st.button("Provide Question", type="primary")
    if provide_question_button:
        path = os.path.relpath("pages/📖_questions.py")
        st.write(path)
        st.switch_page(str(path))


def main():
    """Run the main function."""
    st.sidebar.title("AI Math Tutor")

    grade_dropdown = st.sidebar.selectbox(
        "Select Grade",
        [
            "pre-K",
            "K",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
        ],
    )

    user_dict = {"user": "test_user", "grade": grade_dropdown}

    get_key_concepts_button = st.sidebar.button("Get Started", type="primary")
    if get_key_concepts_button:
        st.session_state.start_get_key_concepts = True

    if (
        "start_get_key_concepts" in st.session_state
        and st.session_state.start_get_key_concepts
    ):
        run_llm_api_get_key_concepts(user_dict)

    clear_chat_button = st.sidebar.button("Reset Usage")
    if clear_chat_button:
        st.session_state.question_history = []


if __name__ == "__main__":
    main()
