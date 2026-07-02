## Project workspace / Cursor usage (practical steps)
- Open the project folder in Cursor IDE and select the folder path to set the workspace.
- Initialize the workspace with UV: run uv init
  - uv init creates files such as .gitignore, python-version, main.py, pyproject.toml
  - pyproject.toml records the minimum Python version (example shown: 3.13)
- Create a virtual environment with UV: uv venv <venv-name>
- Activate the virtual environment using the activation command printed by UV

## requirements.txt and installing packages
- Create requirements.txt listing the libraries to use (examples added during the demo):
  - langchain_grock
  - langchain_mcp_adapters
  - fast_mcp
  - langraph
- Install packages from requirements.txt using UV:
  - uv add -r requirements.txt
- Confirm installations by inspecting the terminal after the install

## Math MCP server (math_server.py) — implementation notes
- Import fast MCP:
  - from mcp.server.fast_mcp import fast_mcp
- Initialize server:
  - mcp = fast_mcp("math")
- Define tools inside the MCP server:
  - add(a: int, b: int) -> int
    - Docstring: "add two numbers"
    - Implementation returns a + b
  - multiply(a: int, b: int) -> int
    - Docstring: "multiply two numbers"
    - Implementation returns a * b
- Run the server using stdio transport inside an if __name__ == "__main__": block:
  - mcp.run(transport="stdio")
- stdio transport behavior:
  - Server uses standard input/output (command prompt) to receive and respond to tool function calls
  - Useful for local testing where client and server communicate through the command line

## Weather MCP server (weather.py) — implementation notes
- Import and initialize fast MCP similar to math server:
  - mcp = fast_mcp("weather")
- Define a get weather tool:
  - get_weather(location: str) -> str
    - Docstring: "get the weather location"
    - Demo implementation returns a constant string (example used: "it's always raining in California")
    - In real usage this function can call third-party weather APIs
- Run the server using streamable HTTP transport:
  - mcp.run(transport="streamable_http")
- streamable HTTP transport behavior:
  - Starts an API service with a local URL (default host localhost and default port 8000)
  - MCP endpoints are exposed under /mcp (e.g., http://localhost:8000/mcp)
  - Run with python weather.py to see the running service URL in the terminal

## Multi-server MCP client (client.py) — configuration and usage
- Create a multi-server MCP client configuration mapping each server entry to:
  - Command-based server (stdio transport)
    - command: "python" (or "uv" — either can be used)
    - args: ["math_server.py"]
      - Ensure correct absolute path if the file is not in the current working directory
    - transport: "stdio"
  - HTTP server
    - url: "http://localhost:8000/mcp"
    - Ensure the server is running before calling the client
- Example workflow inside an async main():
  - import os and set up environment variables (e.g., GROCK API key via os.getenv)
  - Create the client from langchain_mcp adapters (multi-server client)
  - Retrieve tools: tools = await client.get_tools()
  - Initialize model: model = chat_grock(<model-name-string>)  (demo referenced a large Qwen/grok model name)
  - Create an agent: agent = create_react_agent(model, tools)
  - Invoke the agent for a task:
    - math_response = await agent.invoke(messages=[{"role": "user", "content": "what is 3 + 5 * 2"}])
    - Access output message content via the last message: math_response["messages"][-1].content
  - Use asyncio.run(main()) to execute the async main function

## Runtime behaviors and observations from the demo
- Interacting with a stdio-backed tool:
  - The math server using stdio does not expose an HTTP URL; interaction happens via standard input/output (command line)
  - The client will drive the subprocess (python math_server.py) and communicate over stdio
- Interacting with an HTTP-backed tool:
  - The weather server using streamable_http exposes an HTTP URL (default localhost:8000/mcp) which the client calls directly
- Combined client behavior:
  - A single multi-server client can integrate and call multiple MCP servers (stdio and HTTP) within the same agent/session
  - Servers run independently; the client aggregates access to them
- LLM output vs. tool return:
  - The tool returns the raw value (e.g., constant weather string); the LLM/agent can append additional commentary or context to the returned tool output
- Troubleshooting:
  - Occasional runtime errors may occur during demo runs; restarting the client/server processes can resolve transient issues
- Recommended operational note:
  - Close servers when finished; each server process is independently running during testing and integration