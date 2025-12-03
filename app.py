# frontend/app.py
import sys
import os
import streamlit as st
import asyncio
# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.github_agent import run_github_agent

st.title("🤖 GitHub LangGraph MCP Agent")
st.markdown("Ask something like: `list_repositories octocat`")
query = st.text_input("Enter your GitHub query:")

if st.button("Run Agent"):
    if not query.strip():
        st.warning("Please enter a query.")
        st.stop()
        
    with st.spinner("Running GitHub agent..."):
        try:
            response = asyncio.run(run_github_agent(query))
            if response is None:
                st.error("No response received from agent")
                st.stop()
                
            st.subheader("🧠 Agent Response:")
            if "error" in response:
                st.error(response["error"])
            elif "repositories" in response:
                if not response["repositories"]:
                    st.info("No results found")
                else:
                    st.write("Found repositories:")
                    for repo in response["repositories"]:
                        st.markdown(f"- `{repo}`")
            else:
                st.error("Unexpected response format from agent")
        except Exception as e:
            st.error(f"Failed to execute query: {str(e)}")
