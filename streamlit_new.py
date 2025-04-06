import streamlit as st
import asyncio
import traceback
from mcp import ClientSession
from mcp.client.sse import sse_client

async def call_tool(server_url: str, article_url: str) -> str:
    """
    Connects to the MCP server using SSE, initializes the session,
    calls the summarize_wikipedia_article tool, and returns the result.
    """
    try:
        async with sse_client(server_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                result = await session.call_tool("summarize_wikipedia_article", arguments={"url": article_url})
                return result
    except Exception as e:
        return f"Error: {e}\n{traceback.format_exc()}"

def main():
    st.title("Streamlit as an MCP Host")
    st.write("Enter the MCP Server SSE URL and a Wikipedia Article URL to fetch and summarize the article.")

    server_url = st.text_input("MCP Server URL", "http://localhost:8000/sse")
    article_url = st.text_input("Wikipedia Article URL", "https://en.wikipedia.org/wiki/India")

    if st.button("Fetch and Summarize Article"):
        st.info("Fetching and summarizing article...")
        try:
            result = asyncio.run(call_tool(server_url, article_url))
            st.subheader("Article Summary")
            st.text_area("Summary", result, height=400)
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
