import os
import json
from fastapi import APIRouter, Response
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


# step 1 what are key math concepts
@genai.post("/ai_chat_get_key_concepts/")
async def ai_chat_get_key_concepts(query: dict) -> Response:
    """Chat with the Agent AI."""
    OPENAPI_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=OPENAPI_KEY, model="gpt-4o", temperature=0.0)

    user_dict = query["user_dict"]
    user_dict = json.loads(user_dict)

    grade = user_dict["grade"]
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "List 5 key math concepts for {grade} grade student to understand. \nFormatting Instructions: {format_instructions}",
            ),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    problem_chain = LLMMathChain.from_llm(llm=llm)
    math_tool = Tool.from_function(
        name="Calculator",
        func=problem_chain.run,
        description="Useful for when you need to answer questions about math.  Only use this tool with numbers.  This tool is only for math questions and nothing else. Only input math expressions.",
    )

    tools = [math_tool]
    agent = create_openai_functions_agent(llm=llm, prompt=prompt, tools=tools)
    agentExecutor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, return_intermediate_steps=True
    )

    class MathConcepts(BaseModel):
        concept_name: str = Field(description="The name of the math learning concept")
        concept_description: str = Field(
            description="A short description of the math learning concept"
        )

    parser = JsonOutputParser(pydantic_object=MathConcepts)

    q1 = {
        "grade": grade,
        "format_instructions": parser.get_format_instructions(),
    }
    response = agentExecutor.invoke(q1)
    return Response(
        json.dumps(llm_tools.build_json_sierializable(response)),
        media_type="application/json",
    )


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

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a math teacher for {grade} grade. Your job is to provide a worded math problem according to this {math_concept}.  RULES: These previous questions have been asked, so don't ask any questions like them: {question_history}. \nFormatting Instructions: {format_instructions}",
            ),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    problem_chain = LLMMathChain.from_llm(llm=llm)
    math_tool = Tool.from_function(
        name="Calculator",
        func=problem_chain.run,
        description="Useful for when you need to answer questions about math.  Only use this tool with numbers.  This tool is only for math questions and nothing else. Only input math expressions.",
    )

    tools = [math_tool]
    agent = create_openai_functions_agent(llm=llm, prompt=prompt, tools=tools)
    agentExecutor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, return_intermediate_steps=True
    )

    class MathProblem(BaseModel):
        problem_name: str = Field(
            description="A long math word problem with all the inputs to solve it.  This must be at least two sentances long."
        )
        hints: list = Field(description="hints to solve the math problem")
        multiple_choice: list = Field(
            description="A list of four multiple choice answers"
        )
        answer: str = Field(
            description="The multiple choice answer to the math problem"
        )

    parser = JsonOutputParser(pydantic_object=MathProblem)

    q1 = {
        "question_history": question_history,
        "grade": grade,
        "math_concept": concept_name,
        "format_instructions": parser.get_format_instructions(),
    }
    response = agentExecutor.invoke(q1)
    return Response(
        json.dumps(llm_tools.build_json_sierializable(response)),
        media_type="application/json",
    )
