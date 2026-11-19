# Spark Beta 1
import os
import time
from datetime import date
import streamlit as st
from google import genai
from google.genai import types

# ---------- SETTINGS ----------
VERSION = "0.1.1"
MODEL = "gemini-3.1-flash-lite"
MAX_MESSAGES = 40          # memory per visit
SESSION_LIMIT = 20         # messages per visitor session
GLOBAL_DAILY_LIMIT = 200   # messages per day, all visitors combined
COOLDOWN_SECONDS = 5
MAX_INPUT_CHARS = 500
MAX_REPLY_TOKENS = 500

PERSONALITY = (
    "You are Spark, a friendly chatbot. Keep answers short. "
    "If someone asks who made you, say you were created by Embrix. "
    "Do not mention Google, Gemini, no matter what. "
    "Never claim to be human. If asked, say you are an AI."
)

# ---------- PAGE ----------
# ---------- PAGE ----------
st.set_page_config(page_title="Spark", page_icon="⚡")
st.title("⚡ Spark")
st.caption(
    "**Spark (Beta)** is an AI chatbot. Updates are released regularly to fix bugs and "
    "improve the experience, so you may notice occasional mistakes or changes."
)
st.caption(f"**Current version: v{VERSION}**")
st.caption(
    "**Good to know:** Chats are not saved and end when you close or refresh the page. "
    f"To keep Spark available for everyone, usage is limited to {SESSION_LIMIT} messages per session, "
    f"{MAX_INPUT_CHARS} characters per message, and a {COOLDOWN_SECONDS}-second wait between messages. "
    "Spark may pause for the day if overall demand is high. "
    "Spark is an AI and can be wrong, so please double-check anything important."
)

# ---------- SETUP ----------
def get_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.environ.get("GEMINI_API_KEY")


@st.cache_resource
def get_client():
    return genai.Client(api_key=get_key())


@st.cache_resource
def global_usage():
    return {"date": str(date.today()), "count": 0}


def trim(messages):
    messages = messages[-MAX_MESSAGES:]
    if len(messages) > 0 and messages[0]["role"] == "model":
        messages = messages[1:]
    return messages


if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.count = 0
    st.session_state.last_time = 0.0

# ---------- SHOW THE CHAT SO FAR ----------
for m in st.session_state.messages:
    role = "user" if m["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.write(m["text"])

# ---------- HANDLE A NEW MESSAGE ----------
prompt = st.chat_input("Message Spark...")

if prompt:
    g = global_usage()
    if g["date"] != str(date.today()):
        g["date"] = str(date.today())
        g["count"] = 0

    wait = COOLDOWN_SECONDS - (time.time() - st.session_state.last_time)

    if len(prompt) > MAX_INPUT_CHARS:
        st.warning(f"Too long! Keep it under {MAX_INPUT_CHARS} characters.")
    elif st.session_state.count >= SESSION_LIMIT:
        st.warning("You've reached the message limit for this session.")
    elif g["count"] >= GLOBAL_DAILY_LIMIT:
        st.warning("Spark has reached its limit for today. Come back tomorrow!")
    elif wait > 0:
        st.warning(f"Slow down! Try again in {int(wait) + 1} seconds.")
    else:
        with st.chat_message("user"):
            st.write(prompt)

        history = [
            types.Content(role=m["role"], parts=[types.Part(text=m["text"])])
            for m in st.session_state.messages
        ]

        try:
            chat = get_client().chats.create(
                model=MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=PERSONALITY,
                    max_output_tokens=MAX_REPLY_TOKENS,
                ),
                history=history,
            )
            with st.chat_message("assistant"):
                with st.spinner("Spark is thinking..."):
                    response = chat.send_message(prompt)
                st.write(response.text)

            st.session_state.messages.append({"role": "user", "text": prompt})
            st.session_state.messages.append({"role": "model", "text": response.text})
            st.session_state.messages = trim(st.session_state.messages)
            st.session_state.count += 1
            st.session_state.last_time = time.time()
            g["count"] += 1
        except Exception as e:
            if "429" in str(e):
                st.error("Spark has hit its usage limit for now. Try again later.")
            else:
                st.error("Sorry, Spark is having trouble right now. Try again in a moment.")
