# Course structure (three parts)
- Part 1 (fundamentals, ~2–3 hours)
  - Build a chatbot
  - Integrate tools (single + multiple)
  - Add memory
  - Add human-in-the-loop feedback during graph execution
  - Streaming techniques
  - Build MCP (MCP server/client) from scratch
  - Langraph fundamentals: state, graphs, nodes, edges, Graph API
- Part 2 (advanced, ~2 hours)
  - Advanced Langraph concepts: workflows and agents
  - Multi-agent communication for complex workflows
  - Multi-state management across agents
  - Functional API (alternative to Graph API)
  - Debugging & monitoring in Langraph Studio (using lang)
- Part 3
  - End-to-end projects
  - LM ops pipeline and deployment techniques
  - Evaluation techniques and metrics for LLMs (MLflow, Grafana)
  - Deployment with Hugging Face Spaces and cloud integrations

# Environment and project initialization (practical setup)
- Recommended package/project manager: UV (Fast Python package & project manager written in Rust)
  - Advantages mentioned:
    - 10–100× faster than pip
    - Single tool to replace pip, pip-tools, pipx, poetry, pyenv, twine, virtualenv management, etc.
    - Comprehensive project management, universal lock file, can manage Python versions per project
- Basic workflow with UV:
  - Install UV (pip install uv if needed)
  - Initialize project: uv init
    - Creates files: .gitignore, python-version, main.py, pyproject.toml, etc.
    - pyproject.toml sets minimum Python version (example shown: 3.13)
  - Create virtual environment: uv venv <venv-name>
  - Activate virtual environment using the printed activation command
  - Install dependencies from requirements.txt using: uv -r requirements.txt
- Jupyter usage in the project:
  - Install ipykernel into the environment: uv add ipykernel (or pip install ipykernel)
  - Select the environment kernel in Jupyter notebooks

# Key libraries used in examples
- langraph
- langchain
- lang (for tracking & evaluation in Langraph cloud)
- langchain_grock (for Grock-backed chat models)
- langchain_tavly (Tavly web search integration)
- fast MCP (for building MCP servers/clients)
- langchain adapters / MCP adapters (for MCP integration)

# Graph API vs Functional API
- Two ways to build workflows in Langraph:
  - Graph API (recommended by speaker as easiest for learning Langraph)
  - Functional API (alternative, more advanced once familiar with Graph API)
- Speaker uses Graph API for teaching fundamentals and practical examples.

# Langraph core components
- Node
  - Unit of computation/behavior in the graph
  - Each node has a node implementation (functionality)
  - Example node implementations: transcript generator, title generator, content generator, chatbot, tool node
- Edge
  - Represents flow of information from one node to another
  - Edges connect start -> node -> end, or node -> node
- State
  - Shared data structure that holds variables accessible to any node in the graph
  - Example state variables for a YouTube→blog workflow:
    - transcript (output of transcript generator node)
    - title (output of title generator node)
    - content (output of content generator node)
  - Graph + State = "state graph" (maintains context across nodes)
  - Distinct from external memory; state is the in-graph shared context (memory discussed separately)

# Example workflow (YouTube video → transcript → title → content)
- Workflow steps:
  1. Start node: input = YouTube URL
  2. Node A: transcript generator
     - Input: YouTube URL
     - Output: transcript (saved into state variable transcript)
  3. Node B: title generator
     - Input: transcript (from state)
     - Implementation: LLM + prompt → generates title → save into state variable title
  4. Node C: content generator
     - Input: title + transcript (from state)
     - Implementation: LLM + prompt → generates content → save into state variable content
  5. End node: collect/display outputs
- Graph API expresses nodes, edges, and shared state to execute this workflow and see execution trace.

# Reducers and message history
- Use-case: chatbot conversation where messages should be appended (not overwritten) across multiple invocations
- Reducer concept:
  - A reducer defines how a state key (like messages) should be updated
  - Example reducer: add_messages — appends a message to a list rather than overwriting it
- Type/annotation usage in state:
  - Annotated is used to attach metadata to a type (speaker showed examples)
  - State class can be declared to return a dictionary-like type (type dict at runtime equivalent to a plain dict)
  - Example state member:
    - messages: Annotated[list, add_messages] — list that uses add_messages reducer to append messages
  - Purpose: maintain conversation history across graph executions; each node can access messages variable

# Building a basic chatbot with Graph API (concept and steps)
- Import relevant symbols: StateGraph, start, end, reducers (add_messages), message utilities
- Define state class:
  - messages variable: Annotated[list, add_messages]
  - State class declared to return a dict-like type
  - Docstring clarifies that add_messages appends instead of overwriting
- Prepare LLM:
  - Load environment keys (load_env or similar)
  - Initialize model:
    - Example ways:
      - Using a provider-specific chat class (chat_grock from langchain_grock)
      - Using a generic init_chat_model function (providing model string like "grock:llama-3-8b-8192" or "openai:..."), selectable per user
- Define node implementation (chatbot node):
  - Signature: node(state: State) -> return messages
  - Implementation: return llm.invoke(state.messages)
    - llm.invoke reads state.messages as input and produces an AI response that is appended via the reducer
- Graph building:
  - Create builder: builder = StateGraph(state=State)
  - Add nodes: builder.add_node("<node-name>", <node-definition>)
  - Add edges: builder.add_edge(start, "<node-name>"); builder.add_edge("<node-name>", end)
  - Compile: graph = builder.compile()
- Visualization:
  - Use IPython.display Image/display with graph.get_graph().draw_mermaid_png() (speaker used a try/except wrapper)
- Invocation:
  - Synchronous invocation: graph.invoke(messages=[human message])
  - Streaming invocation: graph.stream(...) or graph.stream_events(...)

# Running and streaming the graph
- graph.invoke(messages=...) executes the graph and returns final outputs
- graph.stream(...) yields events; iterating events returns high-level events
- Event value extraction:
  - Iterating event.values shows the AI message content during streaming
  - Example: for event in graph.stream(...): for value in event.values: print(value["messages"][-1].content)
- Two main streaming modes explained:
  - mode = "updates"
    - Streams only the message that is currently getting updated (typically the latest AI message)
    - Useful to see the currently changing node output
  - mode = "values"
    - Streams the appended list of messages (entire conversation history as values)
    - Appends new human/AI messages so you can stream the cumulative conversation
- Synchronous vs asynchronous:
  - There are sync and async stream methods (speaker referenced both; streaming patterns apply to either)
- graph.stream_events(...) returns detailed per-event information useful for debugging (more granular event stream)

# Integrating external tools with the chatbot
- Motivation:
  - LLMs lack live/external knowledge for queries like "recent AI news"
  - Tools provide live data (web search, custom functions, APIs)
- General pattern:
  - Bind tools to the LLM so the LLM can reason about calling them
  - Provide docstrings for each tool so the LLM understands inputs/args and purpose
  - Create a tool node in the graph that executes tool calls and returns tool outputs
- Example tools:
  - Tavly web search (langchain_tavly.TavlySearch with max_results parameter)
    - Initialize Tavly search tool and add to tools list
  - Custom function turned into a tool (example: multiply(a: int, b: int) -> int)
    - Provide a docstring describing function signature (parameters & return)
- Binding tools:
  - llm.bind_tools(tools) produces an llm-with-tools runnable
  - This bound LLM can make tool calls based on the input and tool docstrings
- Tool node and tool condition:
  - Use prebuilt ToolNode to host tools as a node implementation
  - Use ToolsCondition (prebuilt) to route graph execution based on whether the assistant’s latest message is a tool call
    - If latest message from assistant indicates a tool call → route to tool node
    - If not a tool call → route to end node
  - Graph edges:
    - start → tool_calling_llm
    - tool_calling_llm → conditional: (if tool call → tools node) else → end
    - tools → end (or, for agent pattern, tools → tool_calling_llm — see React Agent)
- Observed behavior in examples:
  - "Provide me recent AI news" → LLM triggers Tavly search tool call → tool returns search results → tool output appended to messages
  - "What is 5 * 2?" → LLM triggers multiply tool call → multiply returns 10 → appended to messages
  - Combined inputs (both web query + multiply in same prompt) show LLM can identify and call multiple tools when designed appropriately

# React agent architecture (LLM + tools iterative interaction)
- Problem addressed:
  - Single tool-call flow (start → tool → end) may prematurely end when multiple tool calls or chained reasoning are required
- React agent pattern:
  - Instead of tools → end, have tools → tool_calling_llm (loop back)
  - LLM acts as controller/brain and iteratively:
    - Act: choose an action (call a tool)
    - Observe: receive tool output
    - Reason: decide next action (call another tool or finish)
  - This loop continues until the LLM decides the answer is complete
- Key agent terms:
  - Act — LLM issues tool calls
  - Observe — LLM ingests tool outputs
  - Reason — LLM decides next step (call tool again or finish)
- Benefit: enables multi-step tool usage in one session (e.g., search then compute then summarize)

# Memory and persistent checkpointing
- Purpose:
  - Persist conversational/session state across multiple graph invocations (persistent checkpointing)
  - Solve the problem where information provided in earlier turns is not available in later turns unless explicitly persisted
- Memory saver (checkpointer) concept:
  - Langraph provides a checkpointer memory saver (in-memory example used)
  - Example import (speaker): from langraph.checkpointer.memory import MemorySaver (naming per transcript)
  - MemorySaver stores checkpoints in memory (default dictionary)
- Usage:
  - Create memory saver object
  - When compiling the graph, pass the memory saver via the checkpoint parameter: builder.compile(checkpoint=memory_saver)
  - Use configurable thread ID to separate sessions:
    - Create a config dict containing a configurable->thread key with a unique thread id for that session
    - Example: config = {"configurable": {"thread": "<unique-thread-id>"}}
    - Provide config during invocation: graph.invoke(messages=..., config=config)
  - With the same thread ID, later invocations will see prior saved messages and can answer context-dependent queries (e.g., "What is my name?" after previously stating the name)
- Example behavior:
  - User: "Hi, my name is Kush" → graph invocation saves that in MemorySaver under thread ID
  - Later: "What is my name?" → graph invocation with same thread ID uses saved context and answers correctly

# Streaming recap (modes & detailed events)
- stream / astream methods provide streaming access to graph execution
- Two parameters in streaming relevant to message output: mode parameter values = "updates" or "values"
  - updates:
    - Stream the message currently being updated (most-recent AI message)
    - Does not yield every human message or the full history each time
  - values:
    - Stream the cumulative values (appended conversation history)
    - Each streamed output includes the growing chat history (human + AI messages)
- stream_events provides low-level events for debugging across nodes and messages (more granular view of execution stages)

# Human-in-the-loop (human feedback during graph execution)
- Pattern:
  - Define a human assistance tool that accepts a query string and returns a human response string
  - Provide a docstring explaining "request assistance from a human" so LLM chooses this tool when appropriate
  - When the tool node executes and selects the human assistance tool, it generates an interrupt — execution pauses and waits for human input
- Interrupt/resume mechanics:
  - Use interrupt / command primitives (speaker imported "command" and "interrupt") to pause and resume the workflow
  - Human provides feedback text; the application uses a resume command with data = human_response to resume the execution
  - Example flow:
    1. User asks for expert guidance
    2. LLM chooses a human assistance tool call (tool call shown in messages)
    3. The graph execution interrupts and waits for human input
    4. Human provides guidance text
    5. Application issues a resume command (with human response data)
    6. Graph execution resumes and the AI produces the follow-up or final output
- Use cases:
  - Human approval checkpoints in complex workflows
  - Expert guidance or verification during agent workflows

# MCP (Micro-Connector Protocol) architecture and building MCP servers/clients
- High-level architecture:
  - MCP Server(s)
    - Houses tools (third-party services, custom computations, APIs)
    - Provides tool metadata, prompts, and context to clients
  - MCP Client
    - Maintains a one-to-one connection with server
    - Acts from within the app to call tools exposed by MCP servers
  - App
    - Desktop/cloud/web application embedding the client
- Purpose:
  - Let LLMs/apps request and use remote tools via a protocolized interface (MCP) for live data and functionality
- Transport options (examples discussed)
  - stdio (standard input/output)
    - Server uses stdin/stdout to receive tool functional calls and respond
    - Useful for simple local client-server pipelines e.g., subprocess-style communication
  - HTTP / other transports
    - Used for networked MCP servers (discussed conceptually; speaker will compare later)
- Libraries and adapters:
  - fast MCP: Python library to build MCP servers and clients easily
  - langchain adapters (langchain mcp adapters) to wire MCP into Langchain ecosystems
- Building a simple MCP server (math tools example)
  - Create a server file (example: math_server.py)
  - Import fast MCP (speaker: from MCP.server.fast_mcp import fast_mcp / instantiate fast MCP)
  - Initialize MCP server object (example variable name: mcp = fast_mcp("math"))
  - Define tools on the server:
    - add(a: int, b: int) -> int
      - Docstring: "add two numbers"
      - Implementation: return a + b
    - multiply(a: int, b: int) -> int
      - Docstring: "multiply two numbers"
      - Implementation: return a * b
  - Run the MCP server:
    - Example: if __name__ == "__main__": mcp.run(transport="stdio")
    - The transport="stdio" argument tells the server to use standard input/output to receive and respond to tool function calls
- Client-side behavior:
  - Client will call MCP server tools via the chosen transport
  - When transport = stdio, client interacts with server via subprocess stdin/stdout or appropriate piping
- Speaker intends to show:
  - How to implement MCP servers (math and weather examples)
  - How to run them with different transports (stdio vs HTTP)
  - How to integrate MCP servers with Langchain/Langraph via adapters
  - Practical step-by-step coding and demos (server, client, app integration)

# Practical tips / gotchas mentioned during the session
- After adding environment keys (API keys) into .env, restart the kernel so the new env values are loaded
- When updating function/tool code (e.g., adding return statements), recompile the graph to pick up changes
- Tool docstrings are crucial: they tell the LLM how to call the tool (arguments, intent) and are used during tool-binding decisions
- When testing streaming and modes, use unique thread IDs to isolate sessions and results
- Use MemorySaver/checkpointer configured during graph compile time to enable persistent session behavior across invokes

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