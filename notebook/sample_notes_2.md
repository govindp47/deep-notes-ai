## React agent (reasoning and acting) — implementation details (continued)

- SystemMessage usage
  - System messages are the same strings often written as "you are a helpful assistant."
  - Two equivalent ways to provide a system prompt to the model:
    - Pass the raw string directly.
    - Pass a SystemMessage object (preferred for readability).
  - Recommendation: use SystemMessage so the model and readers know explicitly this is a system-level message.

- BaseMessage / class hierarchy (brief)
  - BaseMessage is the parent class for all message types; AIMessage, HumanMessage, ToolMessage, SystemMessage inherit from it.
  - Child message classes add specific properties (example: ToolMessage includes content and a tool call ID).

- Reducer + typed state for agent messages
  - Use Annotated[Sequence[BaseMessage], add_messages] to:
    - Declare the messages list type.
    - Attach the add_messages reducer so node updates are appended (not overwritten).
  - Reducer behavior summary:
    - Without a reducer, a node update would replace the existing messages attribute.
    - add_messages aggregates/appends new messages into the existing list automatically.

- Tools: decorator, docstring, and argument binding
  - Register a Python function as a tool using the @tool decorator.
  - The tool function must include a docstring: the docstring is required because the LLM uses it as the tool description; omitting it causes an error.
  - Function parameters (e.g., a: int, b: int) are automatically extracted and passed by the model when it decides to call the tool.
  - The LLM decides which tool to call and what arguments to pass; the tool simply executes with those arguments.

- Tool-node / loop wiring
  - Bind model to tools with model.bind_tools(tools).
  - Graph wiring for a React-style loop:
    - Agent node → conditional edge → tool node or end.
    - Tool node → directed edge → agent node (this back-edge creates the loop).
  - The conditional edge function (should_continue) examines state/messages to decide whether to route to the tool node (continue) or to the end (finish).
  - The model can call multiple tools sequentially within one user request; each tool call becomes a tool message that the agent inspects when deciding the next edge.

- Model invocation details
  - When invoking the model, include both the system message(s) and the human message query in the messages list; otherwise the model has no query to process.
  - Compact state update pattern relies on the reducer to append the model response into state.messages rather than directly mutating the list in the node.

- Observed behaviors & constraints
  - Tool calls demonstrate the LLM does not internally compute (e.g., arithmetic) but delegates to tools; the LLM decides which tool and builds the argument values.
  - The LLM may choose not to call any tool and answer directly (e.g., return a joke). The graph handles both tool-using and non-tool responses seamlessly.
  - Docstrings for tools are necessary: without them the graph/tool integration fails.

## Drafter (document drafting agent)

- Design rationale
  - Purpose: interactive human–AI drafting system with iterative updates and final save.
  - Distinction from a pure React agent: the save tool must terminate the process when used (save should lead to end, not back to agent).

- Global variable workaround for injected state
  - Injected state is the Langraph mechanism for passing runtime state into tools; it was not used here.
  - Workaround: store current document content in a global variable that tools read/update; the save tool reads that global variable to write the file.

- Agent state
  - messages annotated Sequence[BaseMessage] with add_messages reducer (preserves appends).

- Tools
  - update(content: str)
    - Purpose: update the global document with provided content.
    - Behavior:
      - Declares global document variable in the function.
      - Updates the global document content.
      - Returns a confirmation string such as "Document has been updated successfully. The current content is: <content>" to the LLM.
  - save(file_name: str)
    - Purpose: save the current document to a text file and finish the process.
    - Behavior:
      - Enforce .txt suffix: if file_name does not end with ".txt", append ".txt".
      - Read the global document content and write it to the specified file.
      - Wrap file I/O in try/except and return informative error text if saving fails.
    - Docstring must indicate that the saved output is a text file so the LLM will supply a .txt name.

- Agent node (r_agent)
  - System prompt: instruct the model that it is "Drafter" — a helpful writing assistant that uses update/save tools, shows current document after modifications, and stops when the human is satisfied.
  - Initialization / robustness:
    - If state.messages is empty → prompt user: "I'm ready to help you update a document. What would you like to create?"
    - Else → prompt user: "What would you like to do with the document?" and print the current document to the terminal.
  - Execution:
    - Combine system prompt, existing state.messages, and the new human message into a messages list.
    - Invoke model.invoke(messages).
    - Print AI response and tool messages to terminal in a readable format.
    - Return the updated state (relying on add_messages to append).

- Conditional edge (should_continue)
  - Examines recent tool messages to determine which tool was used.
  - Routing logic:
    - If the last tool used is save → return "end" (terminate).
    - Otherwise (e.g., update) → return "continue" (route back to tools/agent loop).
  - Default: if no messages exist yet, route to continue (robustness).

- Graph wiring
  - Nodes: agent (r_agent) and tools (ToolNode containing update and save).
  - Entry point: agent node.
  - Directed edge: agent → tools.
  - Conditional edge on tools: routes to either agent (continue) or end (save → end).
  - Compile graph into an executable app.

- Runtime behavior (observed examples)
  - Example workflow:
    - User: "Write me an email to Tom saying I cannot make the meeting."
    - Agent uses update tool to modify global document; tool returns confirmation.
    - User gives further feedback; agent updates again via update tool.
    - When user says "Save it please", agent uses save tool, which writes a .txt file.
    - The agent can auto-generate a suitable filename (e.g., "unable_to_attend_meeting.txt") and save without explicit filename from the user.
  - Saved file contents reflect the final document state.
  - The system accepts an initial non-empty messages list (pre-existing document) so it can operate on existing drafts.

- Extensibility suggestions (implementation notes)
  - Add voice features: speech-to-text (e.g., Whisper) and text-to-speech (e.g., ElevenLabs) to enable voice-based drafting.
  - Add a GUI for richer interaction.
  - Integrate a private knowledge base to provide contextual references during drafting.

## Retrieval-augmented generation (RAG) agent

- LLM temperature
  - temperature parameter controls randomness/stochasticity of model outputs.
  - temperature = 0 → more deterministic outputs; higher values increase variability.

- Embeddings and model compatibility
  - Embedding model converts text into vectors for retrieval.
  - Rule of thumb: embedding model must be compatible with chosen LLM (compatibility issues can arise from differing vector dimensions or model families).

- Document loading and chunking
  - Load a PDF document (example: "stock market performance 2024.pdf") using a PDF loader.
  - Chunking parameters:
    - chunk_size: tokens per chunk (example used: 1000).
    - chunk_overlap: number of tokens repeated between consecutive chunks (example used: 200).
  - Purpose of overlap: provide contextual continuity between adjacent chunks during retrieval.

- Vector store (Chroma) setup
  - Use a Chroma vector database to persist embeddings.
  - Specify a local file path and a collection name (example: collection name "stock_market").
  - On first run: create the collection in the specified directory.
  - Store embeddings and metadata for retrieval.

- Retriever
  - Construct a retriever from the vector store.
  - k parameter: number of top similar chunks to return (example used: k = 5).
  - Retrieval mode: similarity search (default).

- Retriever tool
  - Decorate a function as a tool that accepts a query string and returns matching document chunks (or a "no relevant information" message if none found).
  - Tool behavior:
    - If relevant chunks found → return concatenated chunk contents (or structured results).
    - If none found → return an explicit message indicating no relevant info in the documents.

- System prompt and hallucination mitigation
  - System prompt instructs the LLM to answer questions using the loaded document and to always cite specific parts of the document used in answers to reduce hallucination.

- Retriever agent vs LLM agent separation
  - Two-agent structure:
    - LLM agent: formulates queries and may request tool calls.
    - Retriever agent: executes retriever tool calls, validates tool names, and returns tool outputs.
  - Retriever agent validates requested tool names; if the LLM requests an unknown tool, return an error string instructing correct selection.

- Graph wiring
  - Nodes: LLM agent node and retriever agent node (tool node).
  - Conditional edge: from LLM agent → retriever agent when the LLM issues a tool call.
  - Looping behavior: tool outputs re-enter the LLM agent for final answer formulation.

- Runtime / testing observations
  - Running the script builds the Chroma vector store and persists binary files in the specified directory.
  - Example query: "How was the S&P 500 performing in 2024?"
    - Flow: LLM issues a retriever tool call → retriever returns top chunks → LLM composes an answer and cites document parts.
    - The model answer matched the document content (no hallucination) and included citations to the source chunks.
  - Example query outside the document scope: "How did OpenAI perform in 2024?"
    - Retriever returned "document does not provide specific information" → LLM did not hallucinate an answer.

- Practical parameters to tune
  - chunk_size and chunk_overlap (tradeoff between granularity and context).
  - retriever k (number of returned chunks).
  - temperature for model determinism.
