import openai
import streamlit as st
from utils.agent import CHAIN



with st.sidebar:
    openai_api_key = st.text_input(
        "OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"




st.title("💬 Chatbot")
st.caption("🚀 A streamlit chatbot powered by OpenAI LLM")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():

    openai.api_key = openai_api_key
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    response, intermediate = CHAIN.execute({"input": prompt})
    
    if len(intermediate) > 0:
        st.session_state.messages.append({"role": "assistant", "content": f"Intermediate steps: {intermediate}"})
        st.chat_message("assistant").write(intermediate)

    st.session_state.messages.append({"role":"assistant", "content": response})
    st.chat_message("assistant").write(response)
    CHAIN.conversation.append(f"User: {prompt}. Intermediate: {intermediate}. Response: {response}")
