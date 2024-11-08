import os
import json
from fastapi import APIRouter, Response
from typing import List, TypedDict, Optional, Dict, Literal
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.tools import Tool
from langchain.chains import LLMMathChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

genai = APIRouter()


class MathConcepts(BaseModel):
    concept_name: List[str] = Field(
        description="The names of the math learning concepts"
    )
    concept_description: List[str] = Field(
        description="Short descriptions of the math learning concepts"
    )


class MathProblem(BaseModel):
    problem_name: str = Field(
        description="A math word problem with all the information needed to solve it"
    )
    hints: list = Field(description="hints to solve the math problem")
    multiple_choice: list = Field(description="A list of four multiple choice answers")
    answer: str = Field(description="The multiple choice answer to the math problem")


class GraphState(TypedDict):
    grade: Optional[str]
    question_history: Optional[List[str]]
    math_subject: Optional[str]
    initial_question: Optional[str]
    initial_possible_answers: Optional[List[str]]
    final_question: Optional[str]
    final_possible_answers: Optional[List[str]]
    final_correct_answer: Optional[str]
    ai_confirmation_question: Optional[bool]
    ai_confirmation_answer: Optional[bool]
    revision_count: Optional[int]
    message_history: Optional[List[str]]  # Added message_history


MAX_REVISIONS = 5


def get_key_concepts_template():
    template = """List 5 key math concepts for {grade} grade student to understand."""
    return template


@genai.post("/ai_chat_get_key_concepts/")
async def ai_chat_get_key_concepts(query: dict) -> Response:
    """Chat with the Agent AI to get key math concepts."""
    print("\n====================")
    print("Starting key concepts generation")
    print(f"Input query: {query}")

    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4", temperature=0.0)

    user_dict = json.loads(query["user_dict"])
    grade = user_dict["grade"]

    math_concepts_template = get_key_concepts_template()
    math_concepts_filled_in = math_concepts_template.format(**{"grade": grade})

    structured_llm = llm.with_structured_output(MathConcepts)
    response = structured_llm.invoke(math_concepts_filled_in)
    response_dict = response.dict()

    print(f"Generated concepts: {response_dict}")

    output_dict = {
        "retrieval_response": response_dict,
    }
    return Response(json.dumps(output_dict), media_type="application/json")


def get_question_template():
    template = """You are a math teacher for {grade} grade. Your job is to provide a worded math problem according to this {math_concept}. Do not ask a question is similar to previous questions {question_history}.
    RULES: ALL THE DETAILS TO SOLVE THE PROBLEM MUST BE INCLUDED IN THE PROBLEM NAME."""
    return template


def initial_question_answers(state: GraphState) -> GraphState:
    print("--------------------")
    print("Node: initial_question_answers")
    print(f"Initial state: {state}")

    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4", temperature=0.0)

    math_problem_template = get_question_template()

    structured_llm = llm.with_structured_output(MathProblem)
    response = structured_llm.invoke(
        math_problem_template.format(
            grade=state["grade"],
            math_concept=state["math_subject"],
            question_history=state["question_history"],
        )
    )

    # Initialize all state fields
    state["initial_question"] = response.problem_name
    state["initial_possible_answers"] = response.multiple_choice
    state["final_question"] = None
    state["final_possible_answers"] = None
    state["final_correct_answer"] = None
    state["ai_confirmation_question"] = None
    state["ai_confirmation_answer"] = None
    state["revision_count"] = 0

    # Initialize or update message history
    if state.get("message_history") is None:
        state["message_history"] = []

    # Add initial question generation to history
    state["message_history"].append(
        f"Generated Question: {response.problem_name}\n"
        + f"Generated Answers: {response.multiple_choice}"
    )

    print(f"Generated question: {response.problem_name}")
    print(f"Generated answers: {response.multiple_choice}")
    print(f"Message history length: {len(state['message_history'])}")
    return state


def review_question(state: GraphState) -> GraphState:
    print("--------------------")
    print("Node: review_question")
    print(f"Current state: {state}")

    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4", temperature=0.0)

    if state["revision_count"] >= MAX_REVISIONS:
        print("Max revisions reached")
        state["ai_confirmation_question"] = False
        state["message_history"].append(
            "Maximum revision limit reached. Moving to final output."
        )
        return state

    class ValidQuestion(BaseModel):
        valid_question: bool = Field(
            description="Does the question provide enough information to solve the problem?"
        )
        feedback: str = Field(
            description="Specific feedback about why the question is valid or invalid"
        )

    history_text = (
        "\n".join(state["message_history"])
        if state["message_history"]
        else "No previous history"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a math teacher reviewing questions for clarity and completeness.",
            ),
            (
                "human",
                """Previous attempts and feedback:
{history}

Current question to review: {question}

Does this question provide all necessary information to solve the problem? 
If not, explain what's missing or unclear.""",
            ),
        ]
    )

    chain = prompt | llm.with_structured_output(ValidQuestion)
    response = chain.invoke(
        {"question": state["initial_question"], "history": history_text}
    )

    state["ai_confirmation_question"] = response.valid_question
    state["message_history"].append(
        f"Question Review:\n"
        + f"Valid: {response.valid_question}\n"
        + f"Feedback: {response.feedback}"
    )

    if response.valid_question:
        state["final_question"] = state["initial_question"]
    else:
        state["revision_count"] += 1

    print(f"Question validation result: {response.valid_question}")
    print(f"Feedback: {response.feedback}")
    print(f"Revision count: {state['revision_count']}")
    return state


def validate_question_with_langgraph(question_answers_dict: dict):
    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4", temperature=0.0)

    try:
        question = question_answers_dict["problem_name"]
        possible_answers = question_answers_dict["multiple_choice"]
        history = question_answers_dict.get("history", "No previous history")
    except KeyError as e:
        print(f"Error accessing question data: {e}")
        raise

    llm_math = LLMMathChain.from_llm(llm=llm)
    word_problem_tool = Tool(
        name="MathReasoningTool",
        func=llm_math.run,
        description="A tool that helps you solve logic-based questions",
    )

    tools = [word_problem_tool]
    llm_with_tools = llm.bind_tools(tools=tools)

    class MathQuestion(BaseModel):
        answer_1: bool = Field(description="Is the first answer correct?")
        answer_2: bool = Field(description="Is the second answer correct?")
        answer_3: bool = Field(description="Is the third answer correct?")
        answer_4: bool = Field(description="Is the fourth answer correct?")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a teacher validating math problem answers."),
            (
                "human",
                """Previous history:
{history}

Question: {question}
Possible answers: {answers}
Please validate each answer and indicate which ones are correct.""",
            ),
        ]
    )

    chain = prompt | llm_with_tools.with_structured_output(MathQuestion)
    response = chain.invoke(
        {"question": question, "answers": possible_answers, "history": history}
    )

    validation_results = {
        "answer_1": response.answer_1,
        "answer_2": response.answer_2,
        "answer_3": response.answer_3,
        "answer_4": response.answer_4,
    }

    if not any(validation_results.values()):
        print("Warning: No correct answers found in validation")

    return validation_results


def review_answer(state: GraphState) -> GraphState:
    print("--------------------")
    print("Node: review_answer")
    print(f"Current state: {state}")

    try:
        question = state["initial_question"]
        possible_answers = state["initial_possible_answers"]
        history_text = (
            "\n".join(state["message_history"])
            if state["message_history"]
            else "No previous history"
        )

        question_answers_dict = {
            "problem_name": question,
            "multiple_choice": possible_answers,
            "history": history_text,
        }

        validation_dict = validate_question_with_langgraph(question_answers_dict)
        print("validation from math agent", validation_dict)

        state["ai_confirmation_answer"] = False
        for idx, (answer_key, is_correct) in enumerate(validation_dict.items(), 1):
            if is_correct:
                state["ai_confirmation_answer"] = True
                state["final_possible_answers"] = state["initial_possible_answers"]
                state["final_correct_answer"] = state["initial_possible_answers"][
                    idx - 1
                ]
                if not state["final_question"]:
                    state["final_question"] = state["initial_question"]

                state["message_history"].append(
                    f"Answer validation successful:\n"
                    + f"Correct answer found: {state['final_correct_answer']}"
                )
                print(f"Found correct answer: {state['final_correct_answer']}")
                break

        if not state["ai_confirmation_answer"]:
            print("No correct answer found")
            state["revision_count"] = state.get("revision_count", 0) + 1
            state["message_history"].append(
                "No correct answer found in current options. Requesting revision."
            )

    except Exception as e:
        error_msg = f"Error validating answer: {e}"
        print(error_msg)
        state["revision_count"] = state.get("revision_count", 0) + 1
        state["ai_confirmation_answer"] = False
        state["message_history"].append(error_msg)

    return state


def review_question_decision(
    state: GraphState,
) -> Literal["review_answer", "initial_question_answers"]:
    print("\n--------------------")
    print("Decision: review_question_decision")
    decision = (
        "review_answer"
        if state["ai_confirmation_question"]
        else "initial_question_answers"
    )
    print(f"Decision result: {decision}")
    return decision


def review_answer_decision(
    state: GraphState,
) -> Literal["summarize_output", "initial_question_answers"]:
    print("\n--------------------")
    print("Decision: review_answer_decision")
    decision = (
        "summarize_output"
        if state["ai_confirmation_answer"]
        else "initial_question_answers"
    )
    print(f"Decision result: {decision}")
    return decision


def summarize_output(state: GraphState) -> Dict:
    print("--------------------")
    print("Node: summarize_output")
    print(f"Final state: {state}")

    final_question = state.get("final_question") or state.get("initial_question")
    final_possible_answers = state.get("final_possible_answers") or state.get(
        "initial_possible_answers"
    )

    state["message_history"].append(
        f"Final Output:\n"
        + f"Question: {final_question}\n"
        + f"Answers: {final_possible_answers}\n"
        + f"Correct Answer: {state.get('final_correct_answer')}\n"
        + f"Total Revisions: {state.get('revision_count', 0)}"
    )

    return {
        "final_question": final_question,
        "final_possible_answers": final_possible_answers,
        "final_correct_answer": state.get("final_correct_answer"),
        "revision_count": state.get("revision_count", 0),
        "initial_question": state.get("initial_question"),
        "initial_possible_answers": state.get("initial_possible_answers"),
        "ai_confirmation_question": state.get("ai_confirmation_question"),
        "ai_confirmation_answer": state.get("ai_confirmation_answer"),
        "grade": state.get("grade"),
        "math_subject": state.get("math_subject"),
        "message_history": state.get("message_history", []),
    }


def create_question_workflow():
    """Create and configure the workflow with proper state handling."""
    workflow = StateGraph(GraphState)

    workflow.add_node("initial_question_answers", initial_question_answers)
    workflow.add_node("review_question", review_question)
    workflow.add_node("review_answer", review_answer)
    workflow.add_node("summarize_output", summarize_output)

    workflow.set_entry_point("initial_question_answers")
    workflow.add_edge("initial_question_answers", "review_question")

    workflow.add_conditional_edges(
        source="review_question",
        path=review_question_decision,
        path_map={
            "initial_question_answers": "initial_question_answers",
            "review_answer": "review_answer",
        },
    )

    workflow.add_conditional_edges(
        source="review_answer",
        path=review_answer_decision,
        path_map={
            "summarize_output": "summarize_output",
            "initial_question_answers": "initial_question_answers",
        },
    )

    workflow.add_edge("summarize_output", END)

    return workflow.compile()


@genai.post("/ai_chat_agent_get_question/")
async def ai_chat_agent_get_question(query: dict) -> Response:
    """Get a validated math word problem question based on Grade, Topic."""
    print("\n====================")
    print("Starting new question generation workflow")
    print(f"Input query: {query}")

    question_history = json.loads(query["question_history"])
    user_dict = json.loads(query["user_dict"])
    math_info_dict = json.loads(query["math_info"])

    app = create_question_workflow()

    result = app.invoke(
        {
            "grade": user_dict["grade"],
            "question_history": question_history,
            "math_subject": math_info_dict["concept_name"],
        }
    )

    print("\n====================")
    print("Workflow completed")
    print(f"Final result: {result}")

    output_dict = {
        "retrieval_response": {
            "problem_name": result.get("final_question", ""),
            "multiple_choice": result.get("final_possible_answers", []),
            "answer": result.get("final_correct_answer", ""),
            "hints": [],
        },
        "workflow_info": {
            "grade": user_dict["grade"],
            "math_subject": math_info_dict["concept_name"],
            "initial_question": result.get("initial_question", ""),
            "initial_possible_answers": result.get("initial_possible_answers", []),
            "final_question": result.get("final_question", ""),
            "final_possible_answers": result.get("final_possible_answers", []),
            "final_correct_answer": result.get("final_correct_answer", ""),
            "ai_confirmation_question": result.get("ai_confirmation_question", False),
            "ai_confirmation_answer": result.get("ai_confirmation_answer", False),
            "revision_count": result.get("revision_count", 0),
            "message_history": result.get("message_history", []),
        },
    }

    return Response(json.dumps(output_dict), media_type="application/json")
