import os
import json
from fastapi import APIRouter, Response
from typing import List
import app.helpers.llm_tools as llm_tools
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import (
    JsonOutputParser,
)
from langchain.tools import (
    Tool,
)
from langchain.chains import LLMMathChain
from langchain.agents import create_openai_functions_agent, AgentExecutor


genai = APIRouter()


class MathConcepts(BaseModel):
    concept_name: List[str] = Field(
        description="The names of the math learning concepts"
    )
    concept_description: List[str] = Field(
        description="Short descriptions of the math learning concepts"
    )


# step 1 what are key math concepts
def get_key_concepts_template():
    template = """List 5 key math concepts for {grade} grade student to understand."""
    return template


@genai.post("/ai_chat_get_key_concepts/")
async def ai_chat_get_key_concepts(query: dict) -> Response:
    """Chat with the Agent AI."""
    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4o", temperature=0.0)
    print("in ai_chat_get_key_concepts")

    user_dict = query["user_dict"]
    user_dict = json.loads(user_dict)

    grade = user_dict["grade"]

    math_concepts_template = get_key_concepts_template()
    math_concepts_filled_in = math_concepts_template.format(**{"grade": grade})

    structured_llm = llm.with_structured_output(MathConcepts)
    response = structured_llm.invoke(math_concepts_filled_in)
    response_dict = response.dict()

    output_dict = {
        "retrieval_response": response_dict,
    }
    return Response(json.dumps(output_dict), media_type="application/json")


class MathProblem(BaseModel):
    problem_name: str = Field(
        description="A long math word problem with all the inputs to solve it.  This must be at least two sentances long."
    )
    hints: list = Field(description="hints to solve the math problem")
    multiple_choice: list = Field(description="A list of four multiple choice answers")
    answer: str = Field(description="The multiple choice answer to the math problem")


def get_question_template():
    template = """You are a math teacher for {grade} grade. Your job is to provide a worded math problem according to this {math_concept}.  RULES: These previous questions have been asked, so don't ask any questions like them: {question_history}. \nFormatting Instructions: {format_instructions}"""
    return template


# step 2 generate a question
@genai.post("/ai_chat_agent_get_question/")
async def ai_chat_agent_get_question(query: dict) -> Response:
    """Get a math word problem question based on Grade, Topic."""
    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4o", temperature=0.0)
    question_history = query["question_history"]

    user_dict = query["user_dict"]
    user_dict = json.loads(user_dict)
    grade = user_dict["grade"]
    question_history = json.loads(question_history)

    math_info_dict = query["math_info"]
    math_info_dict = json.loads(math_info_dict)
    concept_name = math_info_dict["concept_name"]

    math_problem_template = get_question_template()
    math_problem_filled_in = math_problem_template.format(
        **{
            "grade": grade,
            "math_concept": concept_name,
            "question_history": question_history,
            "format_instructions": "The question must be a word problem with a single answer.",
        }
    )

    structured_llm = llm.with_structured_output(MathProblem)
    response = structured_llm.invoke(math_problem_filled_in)
    response_dict = response.dict()

    output_dict = {
        "retrieval_response": response_dict,
    }
    return Response(json.dumps(output_dict), media_type="application/json")
