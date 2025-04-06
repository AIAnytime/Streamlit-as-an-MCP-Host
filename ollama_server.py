import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from html2text import html2text

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.sse import SseServerTransport

# Import Ollama functions for summarization
from ollama import chat, ChatResponse

# Create an MCP server instance with the identifier "wiki-summary"
mcp = FastMCP("wiki-summary")

@mcp.tool()
def summarize_wikipedia_article(url: str) -> str:
    """
    Fetch a Wikipedia article at the provided URL, parse its main content,
    convert it to Markdown, and generate a summary using the Ollama model.

    Usage:
        summarize_wikipedia_article("https://en.wikipedia.org/wiki/Python_(programming_language)")
    """
    try:
        # Validate input
        if not url.startswith("http"):
            raise ValueError("URL must start with http or https.")

        # Fetch the article
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    INTERNAL_ERROR,
                    f"Failed to retrieve the article. HTTP status code: {response.status_code}"
                )
            )

        # Parse the main content of the article
        soup = BeautifulSoup(response.text, "html.parser")
        content_div = soup.find("div", {"id": "mw-content-text"})
        if not content_div:
            raise McpError(
                ErrorData(
                    INVALID_PARAMS,
                    "Could not find the main content on the provided Wikipedia URL."
                )
            )

        # Convert the content to Markdown
        markdown_text = html2text(str(content_div))

        # Create the summarization prompt for Ollama
        prompt = f"Summarize the following text:\n\n{markdown_text}\n\nSummary:"
        
        # Call the Ollama model to generate a summary
        response: ChatResponse = chat(model='deepseek-r1:1.5b', messages=[
            {'role': 'user', 'content': prompt},
        ])
        summary = response.message.content.strip()
        return summary

    except ValueError as e:
        raise McpError(ErrorData(INVALID_PARAMS, str(e))) from e
    except RequestException as e:
        raise McpError(ErrorData(INTERNAL_ERROR, f"Request error: {str(e)}")) from e
    except Exception as e:
        raise McpError(ErrorData(INTERNAL_ERROR, f"Unexpected error: {str(e)}")) from e

# Set up the SSE transport for MCP communication.
sse = SseServerTransport("/messages/")

async def handle_sse(request: Request) -> None:
    _server = mcp._mcp_server
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(reader, writer, _server.create_initialization_options())

# Create the Starlette app with two endpoints:
app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
