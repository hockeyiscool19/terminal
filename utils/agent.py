import openai
from langchain.agents import initialize_agent, AgentType
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.chains import LLMMathChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from langchain.tools.render import format_tool_to_openai_function
from langchain.utilities import SerpAPIWrapper, SQLDatabase
from utils.gmail import GMAIL
import streamlit as st

class Langchain:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    
    def __init__(self):
        self.conversation = []
        self.llm = ChatOpenAI(temperature=0, model="gpt-4", openai_api_key=self.OPENAI_API_KEY)
        self.tools = self.initialize_tools()
        self.agent_executor = self.initialize_agent_executor()
        self.mrkl = initialize_agent(self.tools, self.llm, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

    def initialize_tools(self):
        tools = [
            StructuredTool.from_function(
                name="get_email_info",
                func=GMAIL.get_email_info,
                description="useful for getting the agent's email which is being used",
            ),
            StructuredTool.from_function(
                name="read_emails_in_timeframe",
                func=GMAIL.read_emails_in_timeframe,
                description="Useful for getting all emails in a timeframe.",
            ),
            StructuredTool.from_function(
                name="view_email_contents",
                func=GMAIL.view_email_contents,
                description="Useful for viewing the contents of an email given the emailID.",
            ),
            StructuredTool.from_function(
                name="send_email",
                func=GMAIL.send_email,
                description="Useful for sending an email.",
            ),
        ]
        return tools
    
    def initialize_agent_executor(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful assistant"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        llm_with_tools = self.llm.bind(functions=[format_tool_to_openai_function(t) for t in self.tools])

        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_openai_functions(
                    x["intermediate_steps"]
                ),
            }
            | prompt
            | llm_with_tools
            | OpenAIFunctionsAgentOutputParser()
        )

        agent_executor = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            return_intermediate_steps=True
        )
        return agent_executor
    
    def execute(self, input_data):
        input_data = f"{' '.join(self.conversation)} {input_data}"
        response = self.agent_executor(input_data)
        return response['output'], response['intermediate_steps']
        # return response["output"]
    
# Usage:
CHAIN = Langchain()

