- Course goal: learn Langraph for designing, implementing, and managing graph-based conversational AI workflows; course targets beginners, includes theory, coding exercises, and GitHub solutions.
- Section: type annotations are important because Langraph uses them extensively to define states and avoid runtime/type structure errors.
- Python dicts: flexible key->value maps are efficient but do not enforce value types or structure, causing logical errors in large projects.
- Typed dictionary (TypedDict): implement state schemas as classes inheriting TypedDict to enforce keys and types (example: keys name: str and year: int; instance { "name": "Avengers Endgame", "year": 2019 }).
- Benefits of TypedDict: type safety (reduces runtime errors) and improved readability/debuggability.
- Union type annotation: declare a variable can be one of several types (example: def square(x: Union[int, float]) -> Union[int, float]), prevents passing incompatible types like strings.
- Union usage note: LangChain/Langraph libraries use Union extensively to enable flexible yet type-safe APIs.
- Optional type annotation: allows value or None (example: def nice_message(name: Optional[str]) -> str: greet name or use default if None); Optional[str] means string or None only.
- Any type annotation: means value can be any type (example: def print_value(x: Any): print(x)); use when type cannot be constrained.
- Lambda functions: compact inline functions for small transformations (example: list(map(lambda x: x*x, [1,2,3,4])) -> [1,4,9,16]); useful for concise, efficient code.
- Section: Langraph core elements — preserve these concepts and analogies: state (shared application memory / whiteboard), nodes (functions/operations / assembly-line stations), graph (workflow map / road map), edges (directed connections / train tracks), conditional edges (route by condition / traffic light or if/else), start node (entry point / starting line), end node (workflow stop / finish line).
- Tools vs nodes: tools are specialized utilities (e.g., API fetchers) used by nodes; tool node is a node whose primary job is to run a tool (operator controlling a machine in an assembly line).
- StateGraph: framework that builds, manages, and compiles graph structures, nodes, edges, and data flows (analogy: building blueprint).
- Runnable vs node: runnable is a standardized executable component representing various operations; node typically receives and returns state and updates it; both are composable building blocks (analogy: Lego bricks).
- Langraph message types (common five): HumanMessage (user input), AIMessage (model responses), SystemMessage (instructions/context for model), ToolMessage (tool outputs), FunctionMessage (function/tool call representation).
- Coding section intent: start building graphs before combining LLMs, APIs, and tools to avoid complexity; progress incrementally from simple nodes/graphs to agents.

- Hello World graph (example implementation details and flow):
- Imports: dict, TypedDict, StateGraph (state, schema, graph builder).
- Define agent state schema as TypedDict: class AgentState(TypedDict): message: str.
- Define node as Python function: def greeting_node(state: AgentState) -> AgentState: docstring describes function; update state['message'] by concatenation (e.g., "hey " + state['message'] + " how's your day going"); return state.
- Build graph: graph = StateGraph(AgentState); graph.add_node("greeter", greeting_node); graph.set_entry_point("greeter"); graph.set_finish_point("greeter"); app = graph.compile().
- Invoke graph: result = app.invoke(message="Bob"); final state result['message'] -> "hey Bob how's your day going".
- Caution: graph.compile succeeding does not guarantee runtime/logical correctness.
- Visualize graph via IPython helper to confirm start-node-end layout.

- Exercise: implement a personalized compliment agent that concatenates onto state.message (do not replace it), e.g., input "Bob" -> "Bob, you're doing an amazing job learning Langraph".

- Second graph: multiple inputs (handling lists and multiple fields):
- Imports: TypedDict, StateGraph, List.
- AgentState example: class AgentState(TypedDict): values: List[int]; name: str; result: str.
- Node: def process_values(state: AgentState) -> AgentState: docstring; compute total = sum(state['values']); set state['result'] = f"Hi there {state['name']}, your sum is equal to {total}"; return state.
- Graph: graph.add_node("processor", process_values); set entry/finish to "processor"; app = graph.compile().
- Invocation example: app.invoke(values=[1,2,3,4], name="Steve") -> state with result "Hi there Steve, your sum is equal to 10".
- Debugging tip: print state before/after node action to observe updates; if state.result is not provided on input it may be None—avoid using uninitialized fields as inputs before assignment.

- Exercise: create a graph that accepts name, list of integers, and an operation ("+" or "*") and outputs a message like "Hi Jack Sparrow, your answer is 24" by performing addition or multiplication inside a single node (use if statement within node).

- Third graph: sequential nodes connected by edges:
- AgentState example: class AgentState(TypedDict): name: str; age: str; final: str.
- Two nodes: first_node sets state['final'] = f"Hi {state['name']}"; second_node concatenates age info into state['final'] using concatenation rather than replacement (avoid overwriting); both return state.
- Graph wiring: graph.add_node("first_node", first_node); graph.add_node("second_node", second_node); graph.add_edge("first_node", "second_node"); graph.set_entry_point("first_node"); graph.set_finish_point("second_node"); app = graph.compile().
- Example invocation: app.invoke(name="Charlie", age="20") -> final message "Hi Charlie you are 20 years old".
- Logical error warning: accidentally replacing previously written state attributes (e.g., overwrote final instead of concatenating) causes lost data; fix by concatenating old and new content.

- Exercise: build a 3-node sequential graph that accepts name, age, and list of skills; node1 greets name, node2 describes age, node3 formats skills into a comma-separated string, combine into a single result field like "Linda welcome to the system. You are 31 years old and you have skills in Python, machine learning and Langraph." Hint: use add_edge twice to chain nodes.

- Fourth graph: conditional routing via edges:
- Imports: start, end plus previous primitives (TypedDict, StateGraph).
- AgentState: class AgentState(TypedDict): number1: int; operation: str; number2: int; final_number: int.
- Nodes: adder sets final_number = number1 + number2; subtractor sets final_number = number1 - number2.
- Router node (decide_next_node): inspect state['operation'] and return an edge label (e.g., return "addition_operation" or "subtraction_operation") to indicate routing decision—note: in Langraph this function returns an edge label rather than returning an updated state.
- Important integration detail: because decide_next_node returns an edge label rather than a state, nodes attached via graph.add_node may require a pass-through wrapper (lambda state: state) when registering a node whose action is a router that returns an edge; otherwise the node registration expects a state-returning callable.
- Graph wiring and conditional mapping: graph.add_node("router", decide_next_node, ...) ; graph.add_conditional_edge(source="router", path=decide_next_node, path_map={"addition_operation": "add_node", "subtraction_operation": "subtract_node"}); add edges from add_node and subtract_node to end; compile.
- Example invocation: number1=10, operation='-', number2=5 -> final_number = 5.
- Note: conditional edges implement branching at graph level rather than only in-node behavior.

- Exercise: extend the conditional graph to handle two independent operations across four numbers (two operation pipelines) and output both results; this practices building multiple conditional branches.

- Fifth graph: looping via conditional edges (example generating 5 random numbers):
- Use Random module; AgentState: class AgentState(TypedDict): name: str; numbers: List[int]; counter: int.
- Greeting node: set state['name'] to greeting string and initialize state['counter'] = 0 for robustness (reset bad initial counters like negatives).
- Random node: append random.randint(0,10) to state['numbers']; increment state['counter'] += 1; return state.
- Router function should_continue(state): if state['counter'] < 5 return loop edge label; else return exit edge label.
- Graph wiring: start -> greeting -> random; graph.add_conditional_edge(source="random", path=should_continue, path_map={"loop": "random", "exit": "end"}) and also set edges to finish path; compile as app.
- Invocation example: starting counter = -1 will be overwritten to 0 in greeting, then random node executes 5 iterations and exits when counter reaches 5.
- Debugging tip: use print statements before/after node operations to verify state updates.
- Exercise: implement an autonomous higher-or-lower guessing agent that:
- initializes bounds (lower, upper: 1..20), guesses up to max attempts (7), updates bounds based on hint ("higher" or "lower") produced by hint node, stores guesses and attempts in state, and stops when correct guess or max attempts reached; no human in the loop (agent guesses autonomously).

- Section: introducing AI agents by integrating LLMs into graphs.
- Simple bot (LLM integration basics):
- Imports: TypedDict, List, HumanMessage (from langchain), ChatOpenAI (or appropriate LangChain client), StateGraph, env loader for API keys.
- AgentState example: class AgentState(TypedDict): messages: List[HumanMessage].
- Initialize LLM: lm = ChatOpenAI(model="gpt-4o" or preferred model).
- Node integration: def process(state: AgentState) -> AgentState: response = lm.invoke(state['messages']); print response content; optionally append AIMessage to state; return state.
- Build graph: graph.add_node("process", process); set entry/finish points; compile to app.
- Invocation example: app.invoke(messages=[HumanMessage(content="Hi")]) -> model returns reply; simple loop can be implemented to repeatedly call app.invoke until user exits.
- Limitation: without storing full conversation history in persistent storage, agent cannot remember across separate runs (process state in memory is lost when program exits).

- Chatbot with memory:
- Add AIMessage and Union annotation so messages list can contain both HumanMessage and AIMessage: messages: List[Union[HumanMessage, AIMessage]].
- Node process: response = lm.invoke(state['messages']); append AIMessage(content=response.content) to state['messages']; return state.
- Persist conversation across program runs: write state['messages'] to a text file (conversation log) by iterating messages and writing role/content (label user vs AI), so a conversation can be reloaded externally if desired.
- Token/cost management: conversation history grows with each exchange; to control cost, implement a policy (e.g., trim oldest messages when history length exceeds a threshold) or use summarization/prompt-engineering to limit input tokens.

- React agent (Reasoning And Acting pattern) with tool calling:
- Additional type annotations: Annotated and Sequence explained: Annotated adds metadata/constraints to a type (e.g., Annotated[str, "must be valid email format"]); Sequence is a typed sequence helper for lists and avoids manual list manipulation in nodes.
- Reducer functions: add_messages reducer controls how node updates merge with existing state; use reducer to append messages instead of overwriting.
- Tool creation: use @tool decorator to expose Python functions as tools; each tool must have a clear docstring describing purpose; example tool add(a: int, b: int) returns a + b.
- Bind tools to model: model.bind_tools(tools_list) so LLM can call tools.
- Model call node: def model_call(state): invoke model with combined messages + system prompt; model returns output which add_messages reducer will append to state.
- should_continue function: examine last LLM output/tool calls and return edge label to continue (tool call) or end (no more tool calls).
- Graph wiring: start -> model node; conditional edge from model node decides path to tool node or end; edge from tool node back to model node to create a loop; compile app.
- Demonstration: agent asking "add 3 + 4" triggers tool call to add tool with parameters (3,4), tool returns 7, agent writes final AIMessage with result; add further tools like subtract and multiply and model will select appropriate tool(s) and sequence of tool calls (model decides which tool and arguments).
- Tool docstring requirement: tools must have docstrings describing their inputs and behavior or the graph/tool system will error.

- Drafter mini-project (human-AI collaborative drafting pipeline with save tool):
- Design goals: fast drafting assistant that accepts iterative human feedback, lets human stop when happy, and saves drafts to file.
- Implementation choices: global variable document_content used as a simple workaround for passing state into tools (alternative: injected state but out of scope here).
- Tools:
- @tool update(content: str): update global document_content by appending or modifying content; return status and current content for LLM to display.
- @tool save(file_name: str): write global document_content to a text file file_name (ensure .txt extension) and return save confirmation; after save, workflow should end.
- Agent node: system prompt instructs agent to use update and save tools appropriately and to show current document after modifications; if no messages present ask initial creation question; otherwise ask what to modify and append user input as human message; invoke model; tools invoked by model will update global content and/or save file.
- Graph wiring: start -> agent node -> tools node; conditional edge from tools returns either continue (update used) or end (save used); add edge from tools back to agent to allow iterative human-AI collaboration; compile app.
- Example: draft an email, provide feedback ("specify meeting time"), update tool applies changes, repeat until "save" is issued; save tool writes file like "unable_to_attend_meeting.txt".
- Extensions: integrate speech-to-text (Whisper) and text-to-speech (11Labs) for voice UX, add GUI, add persistent knowledge base, or add injected-state refinements.

- Retrieval-Augmented Generation (RAG) agent:
- Purpose: combine retriever (vector search over documents) + LLM to answer queries grounded in external documents and reduce hallucinations.
- Deterministic LLM: instantiate ChatOpenAI with temperature=0 for more deterministic outputs on factual retrieval tasks.
- Embeddings + chunking:
- Create embeddings model compatible with LLM; chunk documents using RecursiveCharacterTextSplitter with parameters chunk_size=1000 tokens and chunk_overlap=200 tokens (overlap ensures context continuity between chunks).
- Loading documents: use PyPDFLoader to load PDF pages (example document: "Stock Market Performance 2024"), verify number of pages (example: 9 pages).
- Vector store: create Chroma vector store locally (path specified) with collection name (example: "stock_market"); persist embeddings so subsequent runs reuse DB.
- Retriever: create retriever with similarity search and parameter k (top-k chunks to return), e.g., k=5.
- Retriever tool: @tool retriever_tool(query: str) -> str: use retriever to fetch top-k documents; if no relevant documents, return a "no relevant information" message; otherwise concatenate and return retrieved text.
- System prompt and agent: use explicit system message instructing agent to cite document parts used (reduce hallucination) and to behave as a grounded assistant answering queries based on retrieved context.
- Workflow:
- LLM generates output and may request a tool call (retriever_tool) for document content; conditional edge routes to retriever agent if a tool call exists; retriever executes tool and returns tool output (ToolMessage) back into state; LLM re-invokes to produce final answer using tool content.
- Example queries:
- "How was the S&P 500 performing in 2024?" -> retriever retrieves relevant chunks -> LLM returns a grounded summary with citations referencing specific document passages; output matches document content (e.g., ~25% total return).
- Non-covered query (e.g., "How did OpenAI perform in 2024?") -> retriever returns "no relevant information"; LLM avoids hallucination and indicates absence of info in the knowledge base.
- Persisted chroma DB files and collections are stored locally for reuse.

- Operational and engineering notes:
- Use env files to store API keys; load via load_env or similar secure loader.
- Keep docstrings for nodes and tools as they provide required descriptions for LLM/tool coordination.
- Always validate compiled graphs by invoking test inputs; compilation success doesn't guarantee logical correctness.
- For memory persistence across program runs use databases or persisted logs (text files acceptable for prototyping; vector DBs recommended in production for RAG).
- Control token/cost by trimming historical conversation messages, summarizing prior context, or limiting retrieved chunk counts (k).
- Multiple valid implementations exist for loops, routing, and state persistence; select patterns that balance robustness and simplicity for your use case.

- Project suggestions and extensions:
- Implement GUI or web UI around graphs (for Drafter), add voice interfaces (Whisper + TTS), use injected state for tool-state integration, integrate vector DBs for long-term memory, and create more sophisticated tool suites for agent workflows.
- Final encouragement: Langraph enables modular, graph-structured AI agents combining LLMs, tools, and retrieval systems; iterate from simple graphs to complex agentic systems, validate with tests, and refine state and routing logic for reliable production behavior.