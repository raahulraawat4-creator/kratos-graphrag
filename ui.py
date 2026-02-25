import streamlit as st
from workflow import ask_graph

# -----------------------------------
# PAGE CONFIG
# -----------------------------------

st.set_page_config(
    page_title="Kratos GraphRAG Agent",
    page_icon="🧠",
    layout="wide"
)

# -----------------------------------
# CUSTOM CSS (Sleek Dark Mode)
# -----------------------------------

st.markdown("""
    <style>
    .stChatMessage {
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------
# HEADER
# -----------------------------------

st.title("🧠 Kratos GraphRAG Agent")
st.caption("Ontology-aware Neo4j reasoning")

# -----------------------------------
# SESSION MEMORY
# -----------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------
# DISPLAY CHAT HISTORY
# -----------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------------
# USER INPUT
# -----------------------------------

if prompt := st.chat_input("Ask about your graph..."):

    # Show user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing graph..."):
            response = ask_graph(prompt)
            st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })