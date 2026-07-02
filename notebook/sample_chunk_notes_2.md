## React agent (reasoning and acting) — additional practical behaviors
- Tool decorator docstring requirement
  - Every function registered as a tool must include a docstring describing the tool. If a tool lacks a docstring (or description), the graph will raise an error during execution.
  - The docstring is used to inform the LLM what the tool does; omitting it prevents the graph from working correctly.
- Tool-call behavior observed during execution
  - The LLM decides which tool to call and what arguments to pass to each tool.
  - Multiple tool calls can occur in a single agent invocation; repeated tool calls indicate the agent routed through the tool node multiple times (loop via conditional edges).
  - Tool-call counts expose whether the LLM relied on external tools for factual computation (e.g., arithmetic) rather than producing an approximate answer from its internal training data.
  - The agent may choose not to call any tool if the LLM determines no tool is necessary; the agent can still produce a final response without tool usage (e.g., returning a joke).

## Drafter — mini-project (agentic drafting system)
### Objectives and requirements
- Speed up drafting of documents and emails.
- Human–AI collaboration: human provides continuous feedback; the agent updates drafts iteratively and stops when the human is satisfied.
- Fast operation and the ability to save drafts to disk.

### Architecture decisions
- Graph topology: start -> agent -> tools -> end.
- Important deviation from a React agent: the save tool must terminate the process directly (tools -> end) instead of routing back to the agent. Update tool calls should route back to the agent to continue the collaborative loop.

### Implementation notes and workarounds
- Injected state exists in Langraph for passing state into tools, but it was not used here (beyond the course scope). A global variable is used as a practical workaround:
  - Tools update the global document content variable.
  - The save tool reads the global variable to write the text file.
- Agent state schema uses the same typed pattern as earlier examples:
  - messages: Annotated[Sequence[BaseMessage], Reducer(add_messages)] — sequence metadata plus add_messages reducer to append messages rather than overwrite.

### Tools
- Update tool
  - Signature: update(content: str)
  - Docstring: describes that it updates the document with provided content.
  - Behavior: marks the global document content variable with the new content and returns a confirmation message (e.g., "document has been updated successfully; current content is ...").
- Save tool
  - Signature: save(file_name: str)
  - Docstring: states it saves the current document to a text file and finishes the process.
  - Behavior:
    - Ensures the filename ends with .txt; appends .txt if missing.
    - Reads the global document content and writes it to the specified text file.
    - Includes try/except to surface file-write errors for debugging.
    - Returns a confirmation message including the saved filename.
- Tools list: [update, save]
- Bind tools to the LLM with model.bind_tools(tools).

### Agent node (r_agent)
- System prompt: instructs the LLM that it is "Drafter," a writing assistant that will use update/save tools, must always display current document after modifications, and follow a human-in-the-loop workflow.
- Interaction logic (robustness measures):
  - If state.messages is empty: prompt the user with an introductory question (e.g., "I'm ready to help you update a document. What would you like to create?") and store the response as a HumanMessage.
  - If state.messages is non-empty: ask the user "What would you like to do with the document?" and print the current document content to the terminal for context; store the user input as a HumanMessage.
- Invocation: combine system prompt, state messages, and the new user message, then call model.invoke(...) and allow the add_messages reducer to append outputs to state.messages. Return the updated state.
- Terminal formatting: additional helper print functions are used to render AI responses and tool messages prettily (purely display logic, not Langraph-specific).

### Conditional routing (should_continue)
- Purpose: choose between continue (loop back to agent) or end (terminate) after a tool call.
- Logic:
  - If no messages exist, default to continue (robustness).
  - Inspect the most recent tool message to determine which tool was used.
  - If the save tool was used -> return the end edge (terminate the graph).
  - If the update tool was used -> return the continue edge (route back to agent for further edits).

### Graph construction
- Nodes: agent (r_agent) and tools (ToolNode wrapping update & save).
- Entry point: agent.
- Edges:
  - Directed edge agent -> tools (agent invokes tool node when appropriate).
  - Conditional edge from tools -> {continue: agent, end: finish}, where continue uses the update tool path and end uses the save tool path.
- Compile the graph to produce the runnable app.

### Runtime behavior and examples
- Interactive usage: run python drafter.py; agent prompts; user issues drafting instructions; agent uses update tool(s) to modify the global document and displays updates.
- The agent can generate a suitable filename itself when saving; the save tool writes the .txt file and returns the saved filename.
- The saved file contents should match the final document content printed during the session.
- The system supports starting from an empty document or from an existing document by populating the initial messages list before invoking the graph.

### Suggested extensions (non-mandatory)
- Add voice input/output (e.g., OpenAI Whisper for STT, ElevenLabs for TTS).
- Provide a GUI for easier editing.
- Integrate a knowledge base for contextual drafting.

## Retrieval augmented generation (RAG) agent
### Architecture overview
- Graph topology: start -> LLM agent -> (if tool call) retriever agent -> loop back to LLM agent -> ... -> end.
- Two distinct agents:
  - Retriever agent: executes retrieval tool calls and returns document-context results.
  - LLM agent (main): produces tool-call decisions and final answers, consuming retrieved context when available.
- Conditional routing controls the loop (continue when a tool call was produced; end when no tool call is required).

### LLM and embedding model notes
- Set model temperature for desired determinism; temperature=0 yields deterministic outputs.
- Embedding model must be compatible with the LLM and vector store (e.g., matching expected vector dimensions and model compatibility).

### Document loading and chunking
- Use a PDF loader (PyPDFLoader) to load the PDF and count pages; verify file exists and report page count.
- Chunking parameters:
  - chunk_size (e.g., 1000 tokens) — size threshold for creating a new chunk.
  - chunk_overlap (e.g., 200 tokens) — number of tokens duplicated between consecutive chunks to preserve context across chunk boundaries.
  - Use a RecursiveCharacterTextSplitter (or equivalent) to produce chunks from the document pages.

### Vector store (Chroma)
- Create a Chroma vector database to store embeddings.
- Specify storage path and collection name (example: collection name = "stock_market").
- If collection does not exist, create it and persist embeddings to the chosen directory (chroma creates local files such as .bin files).
- Wrap chunked documents with an embedding model and persist them into the Chroma collection.

### Retriever
- Instantiate a retriever from the vector store.
- Set search_type (similarity) and k (number of top chunks to return); example k=5 (returns top 5 relevant chunks).

### Retriever tool implementation
- Tool signature: retriever_tool(query: str) -> str
- Behavior:
  - Query the retriever for the top-k similar chunks.
  - If no relevant chunks are found, return a string indicating no relevant information was found.
  - If relevant chunks exist, aggregate them into a string (or structured list) and return those results to the calling agent.
- Bind the retriever tool to the LLM.

### System prompt and hallucination mitigation
- Provide an explicit system prompt instructing the LLM to answer questions about the loaded document.
- Instruct the LLM to always cite specific parts of the document used in answers to reduce hallucination risk.

### Retriever agent (tool executor)
- The retriever agent inspects the LLM response for tool call instructions.
- If a valid tool name is present (retriever_tool), the agent invokes the tool with the provided arguments and returns the tool output into state.
- If the LLM requested an invalid tool name, return an error-like message asking to select from the available tools.

### Graph construction
- Nodes: llm_agent (main LLM) and retriever_agent (tool executor).
- Conditional edge function (should_continue) inspects whether the latest LLM output contains a tool call; if yes -> invoke retriever_agent; otherwise -> finish and present final answer.
- Compile the graph into a runnable app.

### Testing and verification
- Running the script should:
  - Load the PDF and report the page count (example: 9 pages).
  - Create the Chroma vector store and persist embeddings (local files appear in the specified directory).
- Example query flow:
  - User asks: "How was the S&P 500 performing in 2024?"
  - LLM issues a retriever tool call with the query.
  - Retriever returns the most similar chunks (k=5) to the LLM.
  - LLM responds with an answer and cites document passages.
- Verification example: cited facts (e.g., total return ~25%) can be checked against the original PDF text returned by the retriever; the system should avoid hallucination for queries not present in the document (e.g., "How did OpenAI perform in 2024?") by returning that the document contains no relevant information.
