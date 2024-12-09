import os
import streamlit as st
import google.generativeai as genai
import requests  # To call Tavily API
from dotenv import load_dotenv  # To load .env file

# 🔥 **Load API Keys from .env file**
load_dotenv()

# 🔑 API Keys
gemini_api_key = os.getenv("GEMINI_API_KEY")  # Load from .env file
tavily_api_key = os.getenv("TAVILY_API_KEY")  # Load from .env file

# 🚨 **Check if the keys are loaded properly**
if not gemini_api_key or not tavily_api_key:
    st.error("API keys not found! Please add GEMINI_API_KEY and TAVILY_API_KEY to your .env file.")
    st.stop()

# Configure the genai library for Gemini
genai.configure(api_key=gemini_api_key)

# 🔥 **Short-Term Memory** to store user session data
if "conversation_memory" not in st.session_state:
    st.session_state.conversation_memory = []

if "user_memory" not in st.session_state:
    st.session_state.user_memory = {}

if "tavily_response_memory" not in st.session_state:
    st.session_state.tavily_response_memory = {}

def update_memory(user_id, key, value):
    """
    Updates the user's memory with a specific key-value pair.
    """
    if user_id not in st.session_state.user_memory:
        st.session_state.user_memory[user_id] = {}
    st.session_state.user_memory[user_id][key] = value

def get_user_memory(user_id, key):
    """
    Retrieves the memory for a specific user and key.
    """
    return st.session_state.user_memory.get(user_id, {}).get(key, None)

# 🔥 **Tavily API Integration**
def fetch_from_tavily(query):
    """
    Call the Tavily API to get relevant information.
    """
    try:
        url = f"https://api.tavily.com/search?query={query}&apikey={tavily_api_key}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            return f"Sorry, I couldn't fetch information from Tavily for '{query}'."
    except Exception as e:
        return "An error occurred while calling the Tavily API."

# 🔥 **Gemini Chat Session Setup**
generation_config = {
    "temperature": 1.55,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# 🔥 **Start the Gemini Chat Session**
# Ensure the correct format for `parts` in the conversation history
formatted_history = [
    {"role": message["role"], "parts": [message["content"]]} 
    for message in st.session_state.conversation_memory
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=(
        "You are a helpful assistant. Your main task is to help users by answering questions, providing simple and clear explanations. "
        "If someone says 'search' or 'find', you should ask Tavily to search for the requested information. If the user asks you to 'summarize it', you should summarize the last message. "
        "Be polite, friendly, and accurate in your responses."
    ),
)

# **Start a chat session** (This will allow us to use send_message() correctly)
chat_session = model.start_chat(
    history=formatted_history
)

# 🔥 **Chatbot Response Logic**
def chatbot_response(user_input, user_id="user_1"):
    """
    Handles user input, interacts with Gemini and Tavily, and returns a response.
    """
    try:
        # 🔥 Handle "search" or "find" using Tavily
        if "search" in user_input.lower() or "find" in user_input.lower():
            tavily_response = fetch_from_tavily(user_input)
            update_memory(user_id, 'last_tavily_response', tavily_response)
            st.session_state.tavily_response_memory[user_id] = tavily_response

            if isinstance(tavily_response, list) and len(tavily_response) > 0:
                message_to_gemini = "Summarize the following articles:\n"
                for article in tavily_response[:5]:
                    message_to_gemini += f"Title: {article.get('title', 'No Title')}, Link: {article.get('url', 'No URL')}\n"
                response = chat_session.send_message(message_to_gemini)
                return response.text
            else:
                return "❌ No search results found from Tavily."

        # 🔥 Handle "summarize it"
        if "summarize" in user_input.lower():
            last_tavily_response = st.session_state.tavily_response_memory.get(user_id)
            if last_tavily_response:
                message_to_gemini = "Summarize the following articles:\n"
                for article in last_tavily_response[:5]:
                    message_to_gemini += f"Title: {article.get('title', 'No Title')}, Link: {article.get('url', 'No URL')}\n"
                response = chat_session.send_message(message_to_gemini)
                return response.text

        # 🔥 Handle general queries using Gemini
        response = chat_session.send_message(user_input)
        update_memory(user_id, 'last_user_input', user_input)
        update_memory(user_id, 'last_gemini_response', response.text)
        
        st.session_state.conversation_memory.append(
            {"role": "user", "content": user_input}
        )
        st.session_state.conversation_memory.append(
            {"role": "assistant", "content": response.text}
        )

        return response.text
    except Exception as e:
        return "An error occurred while generating a response. Please try again later."

# 🔥 **Main Streamlit UI**

st.set_page_config(
page_title= "Newsly Bot",
page_icon="🚀"    
)

st.title("Newsly ")
st.write("Chat with an Newsly that can search, summarize, and answer your questions in real-time.")

# Chat input
user_input = st.text_input("Type your message here and press Enter:")

# Handle exit commands
if user_input.lower() in ["q", "exit", "quit"]:
    st.write("Exiting chat. Goodbye! 👋")
    st.stop()

if user_input:
    response = chatbot_response(user_input)
    st.write(f"🤖 ChatBot: {response}")
