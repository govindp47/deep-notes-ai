## Implementing a REAct agent — detailed walkthrough

### Type annotations used
- Annotated
  - Adds metadata to a type without changing the underlying type.
  - Use-case: convey semantic constraints or attach reducer metadata to a TypedDict field.
  - Example usage in state schema:
    - messages: Annotated[Sequence[BaseMessage], add_messages]
- Sequence
  - Type annotation representing an ordered collection.
  - When combined with a reducer it signals Langraph to treat the field as an appendable message sequence rather than a plain list needing manual manipulation.
- TypedDict (Agent state)
  - Define an agent state that captures the conversation as:
    - class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

### Message types (relevant to REAct)
- ToolMessage
  - Represents the output produced by a tool call.
  - Contains content and metadata (e.g., tool call id). This gets merged back into the message stream for the LLM to consume.
- SystemMessage
  - Provides instructions/constraints to the LLM (e.g., "You are a helpful assistant.").
  - Prefer using an explicit SystemMessage object for readability.
- BaseMessage
  - Parent class for all message types (HumanMessage, AIMessage, ToolMessage, SystemMessage). Use Sequenced BaseMessage in state schema so all message types can be stored uniformly.

### Reducer function: add_messages
- Purpose: controls how node updates merge into existing state.
- Without a reducer, state updates would overwrite existing values.
- add_messages appends new messages into the existing messages sequence (prevents accidental overwrites).
- Using Annotated[Sequence[BaseMessage], add_messages] instructs Langraph to perform appends automatically.

### Tools: creation, docstrings, and binding
- Create tools with a decorator (e.g., @tool) and define a Python function whose parameters will be supplied by the LLM when it decides to call the tool.
- Docstrings are mandatory for tools:
  - The tool's docstring tells the LLM what the tool does and how to format arguments.
  - If docstring is missing the graph will error — the LLM needs that descriptive metadata to choose and call tools reliably.
- Example simple tool:
  - @tool
    def add(a: int, b: int) -> int:
        """Addition tool: returns the sum of a and b."""
        return a + b
- Bind tools to the LLM so the model knows the available tool set:
  - model.bind_tools([add, multiply, subtract])

### Agent node (model invocation)
- Create a node whose action calls the underlying chat model:
  - Include a SystemMessage describing the agent role/constraints.
  - Ensure the latest user query is present as a HumanMessage in state.messages before invoking.
  - Invoke model with messages list; the model will produce an AIMessage and may also request tool calls.
- Use concise state updates because add_messages handles appending:
  - return {"messages": response_messages}
- Readability tip: pass an explicit SystemMessage instead of just a raw string for system prompts.

### Routing, conditional edge, and looping
- Use a router function (e.g., should_continue(state)) that examines state and returns an edge name string (e.g., "continue" or "end").
  - The router is provided as the path function for graph.add_conditional_edge and maps returned edge names to target nodes.
- Typical REAct loop:
  - start -> agent -> (conditional: tool node OR end)
  - tool node -> agent (explicit edge to loop back)
- Example router behavior:
  - If the most recent response contains a tool call needed, return "continue" (go to tool node).
  - If no further tool calls are required, return "end" (terminate).

### Behavioral example: arithmetic tools and multi-call sequences
- Tools defined: add, subtract, multiply.
- LLM can:
  - Decide which tool(s) to call and in what order.
  - Provide arguments to each tool (e.g., add -> a=34, b=21).
  - Request multiple successive tool calls in a single session (looping through tool node back to agent).
- Observations:
  - The LLM may call tools multiple times for a single user request (e.g., compute intermediate results then further operate).
  - Tools guarantee correct computations (LLM alone is probabilistic; tools produce deterministic results).
  - The agent aggregates tool outputs (ToolMessages) and then produces a final AIMessage answer.
  - If the LLM doesn't require tools it can answer directly — tools augment, not replace, the base model.

### Implementation caveats
- Docstrings are required for tools because they teach the LLM how to use the tool.
- The LLM chooses tool arguments — ensure robust parsing/validation inside tools when necessary.
- Use clear router logic and consistent edge names to avoid routing errors.

---

## Example: Drafter — human–AI collaborative drafting system

### Problem & requirements
- Objective: speed up drafting documents (emails, documents) with:
  - Human–AI collaboration: human provides iterative feedback and the AI updates the draft.
  - Termination when human is satisfied.
  - Ability to save drafts to disk.
  - Fast interactions and persistence across the drafting session.

### Graph structure and design decision
- Topology:
  - start -> agent -> tools node
  - tools node has two possible next steps:
    - continue -> back to agent (via tools → agent edge)
    - end -> finish (when save tool was used)
- Difference from REAct:
  - Save tool must finish the process (tools → end) instead of looping back to agent.

### Implementation details and workarounds
- Injected state (preferred Langraph pattern) is more correct for tools that need access to state, but it is advanced/out-of-scope here.
- Practical workaround: use a global variable document_content to hold the current draft; tools update/read this variable.
  - update tool writes into global document_content.
  - save tool reads document_content and writes it to disk.

### Tools
- Update tool
  - Signature: update(content: str) -> str
  - Docstring: explains the purpose (update the current draft with provided content).
  - Behavior:
    - Uses global document_content, appends or replaces content as desired.
    - Returns confirmation (ToolMessage) including the current content.
- Save tool
  - Signature: save(file_name: str) -> str
  - Docstring: "Saves the current document to a text file and finishes the process."
  - Behavior:
    - Ensure file_name ends with ".txt"; if not, append ".txt".
    - Write global document_content to disk under file_name with try/except for robustness.
    - Return confirmation message indicating file saved.

### Agent node (r_agent)
- System prompt: instruct model that it is "Drafter, a helpful writing assistant", enumerate how to use update and save tools, ask to always show current document after modifications.
- Runtime behavior:
  - If state.messages is empty:
    - Ask the human what they want to create (introductory prompt).
  - Else:
    - Ask "What would you like to do with the document?" and print current document contents for human context.
  - Combine system message, previous messages, and new HumanMessage, then call the model.
  - Print (for developer/terminal visibility) the AI response and any ToolMessages.
  - Return updated state; add_messages reducer appends messages automatically.

### Router logic (should_continue)
- Examines latest tool usage:
  - If last tool used is save -> return "end" (terminate).
  - If last tool used is update -> return "continue" (go back to agent for further edits).
  - If messages empty -> default to "continue" (start the dialogue).
- This ensures the save tool causes immediate termination instead of looping.

### Example session flow
- User: "Write an email to Tom saying I cannot make the meeting."
  - Agent uses update tool to create initial draft (ToolMessage with current content).
  - Human gives feedback: "Include that the meeting was at 10:00 AM; sign with my name V."
  - Agent uses update tool again to apply changes.
- User: "Save it please."
  - Agent invokes save tool (selects filename or is supplied one).
  - Save tool writes file (e.g., "unable_to_attend_meeting_email.txt") and returns confirmation.
  - Router sends flow to "end"; graph finishes.
- The LLM may generate the file name itself; save tool normalizes filename and saves.

### Robustness measures & extensions
- Robustness:
  - Validate file write via try/except.
  - Print current document after updates to ensure human visibility.
- Extensions:
  - Use injected state to avoid global variables.
  - Add speech support (e.g., Whisper for STT, 11Labs for TTS) to enable voice-based drafting.
  - Build a GUI or integrate a DB/vector store for saved versions and search history.
  - Use commands/interrupts (advanced Langraph features) for richer control flows.

---

## Example: Retrieval-Augmented Generation (RAG) agent

### Architecture overview
- Two-agent loop:
  - LLM agent (crafts responses and decides whether to call retriever).
  - Retriever agent (executes retriever tool calls and returns relevant document chunks).
- Graph flow:
  - start -> llm_agent -> (conditional: retriever_tool OR end)
  - retriever_agent (executes tool) -> llm_agent (loop back)
- Purpose: answer queries grounded in an external document collection (reduce hallucination).

### Key components and parameters
- LLM initialization
  - Set temperature = 0 for deterministic outputs when you want stable factual answers.
- Embedding model
  - Converts text chunks into vector embeddings.
  - Must be compatible with chosen LLM (watch for embedding dimension mismatches).
- Document loading
  - Use a PDF loader (or other loader) to ingest source documents.
  - Example: load a 9-page "Stock market performance 2024" PDF.
- Chunking (RecursiveTextSplitter)
  - chunk_size (e.g., 1000 tokens): maximum tokens per chunk.
  - chunk_overlap (e.g., 200 tokens): overlap tokens between consecutive chunks to preserve context across boundaries.
  - Rationale: chunk_size controls retrieval granularity; overlap reduces edge-effect loss of context.
- Vector DB (Chroma)
  - Store embeddings and chunk metadata in a vector database.
  - Provide file path and collection name (e.g., "stock_market") for persistent storage.
  - Create collection if it doesn't exist on first run.

### Retriever
- Retrieving strategy:
  - Similarity search over embedded chunks.
  - k parameter controls how many top chunks to return (e.g., k = 5).
  - Balance k to get enough context but avoid noise.
- Retriever tool
  - Implemented as a decorated tool: retriever_tool(query: str) -> str
  - Behavior:
    - Run retriever.search(query, k).
    - If no relevant chunks found return a no-relevance message.
    - Else return concatenated chunks (or structured excerpts) as a string ToolMessage.

### LLM system prompt and hallucination mitigation
- Provide a comprehensive system prompt:
  - Instruct: "You are an intelligent AI assistant who answers questions about the document loaded into your knowledge base."
  - Explicitly instruct the model to always cite specific parts of the document used in answers (reduces hallucinations).
- Additional constraints:
  - If retriever returns "no relevant information", the model should report that explicitly rather than invent facts.

### Retriever agent (tool executor)
- Functionality:
  - Parse the LLM's response to detect a requested tool call (tool name + arguments).
  - Validate the requested tool name against available tools (return an error tool response if invalid).
  - Execute retriever_tool(query) when valid and return the result as a ToolMessage appended to state.messages.

### Router logic (should_continue)
- Check if the last message contains a tool call:
  - If yes (tool executed), route to retriever agent to handle tool execution.
  - If no tool call required, route to end and present the final LLM answer.

### End-to-end testing & examples
- Initial run: load PDF -> chunk -> create Chroma vector store -> print confirmation (e.g., "9 pages loaded").
- Example query 1:
  - Q: "How was the S&P 500 performing in 2024?"
  - Flow:
    - LLM issues retriever_tool call with the query.
    - Retriever returns the top-k chunks that reference S&P 500 performance.
    - LLM composes an answer citing exact document passages (e.g., "total return ~25%", "magnificent 7 influence").
    - Output includes citations/references to chunk locations.
- Example query 2 (out-of-domain):
  - Q: "How did OpenAI perform in 2024?"
  - Flow:
    - Retriever finds no relevant chunks.
    - Retriever returns "no relevant information".
    - LLM responds acknowledging no available info (avoids hallucination).

### Practical caveats and best practices
- Embedding compatibility
  - Use embeddings compatible with the LLM or ensure vector dimensionality aligns.
- Temperature control
  - Lower temperature (0) for deterministic, citation-focused outputs; increase for more creative responses.
- Chunk tuning
  - chunk_size and chunk_overlap are tradeoffs: smaller chunks => finer-grained retrieval; overlap helps context continuity.
- k tuning
  - Choose k (top-k chunks) to balance context coverage vs. noise introduction.
- Instruct model to cite
  - Explicit citation instructions in system prompt substantially reduce hallucination risk.

---