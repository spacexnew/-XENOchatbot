import os
import streamlit as st
from openai import OpenAI

# 1. Set up the window and mobile screen layout
st.set_page_config(page_title="XENO Chatbot", layout="centered")
st.title("🤖 XENO Work Assistant")

# 2. Grab your secret API key securely from Render's settings
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 3. Give the bot a memory and tell it its name is XENO
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system", 
            "content": "Your name is XENO. You are a professional, efficient work assistant. Always introduce yourself as XENO if asked. Help organize tasks, summarize information, and draft clear emails."
        }
    ]

# 4. Show the past conversation history on the screen
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 5. Wait for you to type a message on your phone or computer
if prompt := st.chat_input("Talk to XENO..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 6. Send the conversation to OpenAI and display XENO's response
    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages
        )
        answer = response.choices.message.content
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
