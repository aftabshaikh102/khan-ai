import sqlite3
import re
import os
import json
import streamlit as st
from google import genai
from google.genai import types



# -------------------- LONG-TERM MEMORY --------------------

DB_PATH = "khan_memory.db"

def init_memory():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

def save_memory(key, value):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO memories (key, value) VALUES (?, ?)",
            (key, value),
        )

def get_memories():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT key, value FROM memories"
        ).fetchall()
    return dict(rows)

init_memory()


# -------------------- PAGE CONFIG --------------------

st.set_page_config(
    page_title="Khan AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- DEFAULT SETTINGS --------------------

DEFAULT_INSTRUCTION = """
You are Khan AI, a helpful personal AI assistant.

Your responsibilities:
- Explain Python, AI/ML, and cybersecurity in simple language.
- Teach coding step by step, from beginner to advanced.
- Give practical examples, code, and debugging help.
- Explain ethical hacking only for authorized learning and testing.
- Help with study plans, projects, career guidance, and productivity.
- Remember relevant details from the current conversation.
- Use clear headings and structured answers when helpful.
- Ask clarifying questions when necessary.
- Never claim to have permanent memory unless it is actually available.
- Be honest when you are uncertain.
"""

DEFAULT_MODEL = "gemini-3.8-flash"

# -------------------- SESSION STATE --------------------

if "chats" not in st.session_state:
    st.session_state.chats = {
        "Chat 1": []
    }

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Chat 1"

if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = 1

if "system_instruction" not in st.session_state:
    st.session_state.system_instruction = DEFAULT_INSTRUCTION

if "model" not in st.session_state:
    st.session_state.model = DEFAULT_MODEL

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

if "last_error" not in st.session_state:
    st.session_state.last_error = None

messages = st.session_state.chats[
    st.session_state.active_chat
]

# -------------------- HEADER --------------------

st.title("🤖 Khan AI")
st.caption("Your personal AI assistant | Powered by Google Gemini")

# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.header("⚙️ Settings")

    if st.button("➕ New conversation", use_container_width=True):
        st.session_state.chat_counter += 1
        name = f"Chat {st.session_state.chat_counter}"
        st.session_state.chats[name] = []
        st.session_state.active_chat = name
        st.session_state.last_error = None
        st.rerun()

    st.divider()
    st.subheader("💬 Your conversations")

    chat_names = list(st.session_state.chats.keys())

    selected_chat = st.selectbox(
        "Select conversation",
        options=chat_names,
        index=chat_names.index(st.session_state.active_chat),
        label_visibility="collapsed",
    )

    if selected_chat != st.session_state.active_chat:
        st.session_state.active_chat = selected_chat
        st.session_state.last_error = None
        st.rerun()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.chats[
                st.session_state.active_chat
            ] = []
            st.session_state.last_error = None
            st.rerun()

    with col2:
        if st.button("🗑️ Delete chat", use_container_width=True):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[
                    st.session_state.active_chat
                ]
                st.session_state.active_chat = next(
                    iter(st.session_state.chats)
                )
                st.rerun()
            else:
                st.session_state.chats[
                    st.session_state.active_chat
                ] = []
                st.rerun()

    st.divider()
    st.subheader("🧠 AI configuration")

    st.session_state.model = st.selectbox(
        "Gemini model",
        options=[
            "gemini-3.8-flash"],
        index=0,
        help="Gemini model available to your API key.",
    )

    st.session_state.temperature = st.slider(
        "Creativity",
        min_value=0.0,
        max_value=1.5,
        value=st.session_state.temperature,
        step=0.1,
        help="Lower values are more predictable.",
    )

    with st.expander("✏️ Customize AI personality"):
        st.session_state.system_instruction = st.text_area(
            "System instructions",
            value=st.session_state.system_instruction,
            height=220,
        )

    st.divider()
    st.subheader("📤 Export conversation")

    current_messages = st.session_state.chats[
        st.session_state.active_chat
    ]

    if current_messages:
        export_text = "\n\n".join(
            f"{'You' if m['role'] == 'user' else 'Khan AI'}:\n"
            f"{m['content']}"
            for m in current_messages
        )

        st.download_button(
            "⬇️ Download as TXT",
            data=export_text,
            file_name="khan_ai_chat.txt",
            mime="text/plain",
            use_container_width=True,
        )

        st.download_button(
            "⬇️ Download as JSON",
            data=json.dumps(
                current_messages,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="khan_ai_chat.json",
            mime="application/json",
            use_container_width=True,
        )

    st.caption("Chat history is stored in the current session.")

# -------------------- QUICK PROMPTS --------------------

st.markdown("### What can I help you with?")

quick_prompts = [
    "🐍 Learn Python",
    "🤖 Explore AI/ML",
    "🔐 Learn Cybersecurity",
    "💻 Build a project",
]

cols = st.columns(4)

for i, label in enumerate(quick_prompts):
    with cols[i]:
        if st.button(label, use_container_width=True):
            prompt_map = {
                "🐍 Learn Python":
                    "Teach me Python from beginner level, step by step.",
                "🤖 Explore AI/ML":
                    "Explain AI and machine learning with practical examples.",
                "🔐 Learn Cybersecurity":
                    "Teach me cybersecurity fundamentals for ethical learning.",
                "💻 Build a project":
                    "Suggest a beginner-friendly Python AI project and guide me through it.",
            }
            st.session_state.pending_prompt = prompt_map[label]
            st.rerun()

# -------------------- DISPLAY CHAT --------------------

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("code"):
            st.code(message["code"], language="python")

# -------------------- API KEY --------------------

def get_api_key():
    """Read the key from Streamlit secrets or environment."""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""

    return key or os.environ.get("GEMINI_API_KEY", "")


# -------------------- GENERATE RESPONSE --------------------

prompt = st.chat_input("Ask Khan AI anything...")

if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    api_key = get_api_key()

    if not api_key:
        st.error(
            "Gemini API key not found. Add GEMINI_API_KEY "
            "to your Streamlit secrets."
        )
        st.stop()

    # Display and store the user message.
    messages.append({
        "role": "user",
        "content": prompt,
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini conversation history.
    # The current prompt is passed separately below.
    history = []

    for message in messages[:-1]:
        history.append(
            types.Content(
                role=(
                    "user"
                    if message["role"] == "user"
                    else "model"
                ),
                parts=[
                    types.Part.from_text(
                        text=message["content"]
                    )
                ],
            )
        )

    
    try:
        client = genai.Client(api_key=api_key)

        with st.chat_message("assistant"):
            with st.spinner("Khan AI is thinking..."):
                response = client.models.generate_content(
                    model=st.session_state.model,
                    contents=history + [
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=prompt)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=st.session_state.system_instruction,
                        temperature=st.session_state.temperature,
                    ),
                )

                answer = response.text or "No text response was returned."
                st.markdown(answer)

        messages.append({
            "role": "assistant",
            "content": answer,
        })

        st.session_state.last_error = None

    except Exception as error:
        st.session_state.last_error = str(error)

        st.error(
            "Khan AI could not generate a response. "
            "Your message has been kept. Check the error below."
        )

        with st.expander("Technical details", expanded=True):
            st.code(str(error))

    except Exception as error:
        st.session_state.last_error = str(error)

        st.error(
            "Khan AI could not generate a response. "
            "Your message has been kept. Check the error below."
    )

        with st.expander("Technical details", expanded=True):
            st.code(str(error))



    st.write("DEBUG: App is running")

test_prompt = st.chat_input("Test message")

if test_prompt:
    st.success(f"Message received: {test_prompt}")
