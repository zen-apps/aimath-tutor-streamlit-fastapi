import json
import streamlit as st
import os

from utils.api_connector import (
    ai_chat_agent_get_question,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = 0

if "question_history" not in st.session_state:
    st.session_state.question_history = []

if "user_dict" not in st.session_state:
    st.session_state.user_dict = {}

if "concept_dict" not in st.session_state:
    st.session_state.concept_dict = {}

user_dict = st.session_state["user_dict"]
concept_dict = st.session_state["concept_dict"]


@st.cache_data()
def get_quetion(session_id, user_dict, concept_dict):
    """Get a math word problem question based on Grade, Topic."""
    llm_response = ai_chat_agent_get_question(
        question_history=st.session_state.question_history,
        user_dict=user_dict,
        math_info=concept_dict,
    )
    st.write(llm_response)

    output = llm_response["retrieval_response"]
    return output


if len(user_dict) == 0:
    st.warning("Please go back to the previous page and select Grade and Math Concept.")
    st.stop()
else:
    resp_dict = get_quetion(
        session_id=st.session_state.session_id,
        user_dict=user_dict,
        concept_dict=concept_dict,
    )

    problem_name = resp_dict["problem_name"]
    st.write(f":orange[{problem_name}]")
    st.session_state.question_history.append(problem_name)

    possible_answers_radio = st.radio(
        "Select the correct answer", resp_dict["multiple_choice"]
    )
    answer_btn = st.button("Submit Answer", type="primary")
    if answer_btn:
        if str(possible_answers_radio) == str(resp_dict["answer"]):
            st.write("Correct!")
            st.balloons()
            st.session_state.session_id += 1

            next_question_btn = st.button("Next Question")
            if next_question_btn:
                path = os.path.relpath("pages/📖_questions.py")
                st.switch_page(str(path))
        else:
            st.write("Incorrect! Try again.")

    hint_list = resp_dict["hints"]
    with st.expander("Show Hints"):
        for hint in hint_list:
            st.write(hint)
    answer = resp_dict["answer"]
