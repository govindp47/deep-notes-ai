# Langraph — Conceptual and Practical Study Notes  

(Notes preserve explanations, examples, comparisons and caveats exactly as presented in the transcript.)

## Type annotations (Python) — relevance to Langraph

- Purpose: Langraph uses Python type annotations extensively (especially for defining states). The section aimed to give a high-level overview of common annotations encountered while coding in Langraph.

- Dictionaries
  - Standard Python dicts are flexible and efficient for lookups, but they do not enforce structure or types. In large projects this lack of structural/type checking can cause logical errors that are hard to find.
  - Example:
    - Simple dict: `movie = {"name": "Avengers Endgame", "year": 2019}`

- Typed dictionaries (type dictionary / TypedDict)
  - Implemented as a class (TypedDict-style). You explicitly declare types for each key.
  - Example (conceptual):
    - Define a class `Movie(TypedDict)` with `name: str` and `year: int`.
    - Instantiate: `movie = Movie(name="Avengers Endgame", year=2019)`
  - Benefits:
    - Type safety: reduces runtime type errors.
    - Improved readability and easier debugging.
  - Note: Typed dictionaries are used to define Langraph states.

- Union
  - Use case: parameter accepts one of several types.
  - Example: function that squares `x: Union[int, float]` — accepts int or float, fails on string.
  - Langraph / LangChain use Union extensively for type safety and catch incorrect usage.

- Optional
  - Equivalent to `Union[T, None]`.
  - Example: `name: Optional[str]`. A function using this can handle `None` explicitly:
    - If `name` is `None` -> branch to "random person"; else use the string.
  - Caveat: Optional restricts to either the given type or `None`, not arbitrary types.

- Any
  - `Any` means the value can be any type; no restrictions. Example: `def print_value(x: Any): print(x)`

- Lambda functions
  - Small anonymous functions as short replacements for one-line functions.
  - Examples:
    - Square function: `square = lambda x: x * x`
    - Use with `map`: `list(map(lambda x: x * x, [1,2,3,4]))` -> `[1,4,9,16]`
  - Benefit: concise, efficient for simple operations.

---

# Langraph core elements (concepts)

(Each concept is presented with the explanations and analogies from the transcript.)

## State

- Definition: shared data structure that holds current information/context of the entire application.
- Role: application memory — stores variables and data nodes can access and modify.
- Analogy: a whiteboard in a meeting room where participants write or update information.
- Note: States in Langraph are typically defined with TypedDict-style classes (type dictionaries).

## Node

- Definition: individual functions/operations that perform specific tasks in a graph.
- Behavior:
  - Each node receives an input (often the current state), processes it, and produces an output / updated state.
- Analogy: station on an assembly line; each station does one specific job.

## Graph

- Definition: overarching structure that maps how nodes are connected and executed.
- Role: visually represents workflow, sequence and conditional parts between operations.
- Analogy: a road map showing routes and intersections (paths to take next).
- Note: graph is the central object (hence Langraph name).

## Edge

- Definition: connection between nodes that determines flow of execution.
- Types:
  - Standard directed edges: define which node runs next.
    - Analogy: train track connecting stations; the state (train) moves along it.
  - Conditional edges: choose next node based on condition/logic applied to current state.
    - Analogy: traffic light decides which direction to go (if/else semantics).
- Implementation detail (introduced later): Langraph supports conditional edges via a method to add conditional mappings (path maps).

## Start point (entry)

- Virtual entry node marking where graph execution begins.
- Does not perform operations itself.
- Analogy: starting line of a race.

## End point (finish)

- Signifies conclusion of workflow; when reached, execution stops.
- Analogy: finish line of a race.

## Tool

- Definition: specialized function/utility that nodes can use (e.g., fetching data from an API).
- Difference from Node:
  - Node: structural element in the graph with state input/output.
  - Tool: functionality used inside nodes.
- Analogy: tools in a toolbox (hammer, screwdriver) — each has a distinct purpose.

## Tool node

- Special kind of node whose main job is to run a tool.
- Example role: a node that calls an API tool and injects the tool's output back into the state.
- Analogy: assembly line operator that controls a machine (tool) and feeds results back to the line.

## StateGraph (the framework object)

- Role: builds and compiles the graph structure; manages nodes, edges and overall state.
- Analogy: blueprint of a building that outlines design and connections.

## Runnable

- Definition: standardized executable component that performs a specific task within an AI workflow.
- Difference from Node:
  - Runnable can represent various operations.
  - Node typically receives a state, performs an action, and updates the state.
- Analogy: Lego bricks that snap together to form complicated structures.

## Message types (common)

- Human message: input from a user.
- AI message: responses generated by AI models.
- System message: provides instructions/context to the model (e.g., "you are a helpful assistant").
- Tool message: similar to function message, specific to tool usage; contains tool output and metadata.
- Function message: represents tool or function call results.
- Note: these are the common message types used within Langraph workflows (similar to LangChain messaging conventions).

---

# Building graphs in Langraph — practical patterns, examples and caveats

(Each graph example below is an actual concept taught; code names and flow are preserved as used in the transcript.)

## Pattern: State schema (TypedDict-style)

- Langraph expects the state schema to be a typed dictionary class.
- Example pattern:
  - `class AgentState(TypedDict):`
    - define attributes with types, e.g. `message: str` or `values: List[int]`
- Rationale: defines structure and types of state attributes used by nodes.

---

## Hello World graph (single node, single input)

- Objectives:
  - Define agent state schema.
  - Create a node function that reads and updates the state.
  - Build, compile, invoke graph; observe data flow through a single node.

- State schema example:
  - `class AgentState(TypedDict):`
    - `message: str`

- Node definition (signature and behavior):
  - Function signature: `def greeting_node(state: AgentState) -> AgentState:`
  - Docstring: important habit — describe node's action (this docstring will tell LLMs what the function does when used later).
    - Example docstring: `"Simple node that adds a greeting message to the state."`
  - Update state inside node:
    - `state["message"] = "hey " + state["message"] + " how's your day going"`
  - Return updated state: `return state`

- Graph construction:
  - Create graph: `graph = StateGraph(state_schema=AgentState)`
  - Add node: `graph.add_node("greeter", action=greeting_node)`
    - Parameters required: node name and action function.
  - Set entry and finish:
    - `graph.set_entry_point("greeter")`
    - `graph.set_finish_point("greeter")`
  - Compile graph: `app = graph.compile()`
    - Caveat: compile success does not guarantee logical correctness; compilation may pass while logic contains errors.

- Invoke graph:
  - `result = app.invoke(message="Bob")` (example)
  - Access state attribute: `result["message"]` -> `"hey Bob how's your day going"`

- Visualization (optional):
  - Use IPython utilities to render graph image (used in the transcript to compare diagram).

- Exercise (from transcript):
  - Create a personalized compliment agent that accepts a name (e.g., `"Bob"`) and outputs `"Bob, you're doing an amazing job learning Langraph."` — hint: concatenate state, not replace.

---

## Graph 2 — multiple inputs and list processing

- Objective: handle multiple inputs with different types (list[int], str), process and update state.

- State schema example:
  - `class AgentState(TypedDict):`
    - `values: List[int]`
    - `name: str`
    - `result: str`

- Node: `def process_values(state: AgentState) -> AgentState:`
  - Docstring: `"Function process handles multiple different inputs."`
  - Operation inside node:
    - Set `state["result"] = f"Hi there {state['name']}. Your sum is equal to {sum(state['values'])}"`
  - Return updated state.

- Graph construction:
  - `graph = StateGraph(state_schema=AgentState)`
  - `graph.add_node("processor", action=process_values)`
  - Set entry and finish points to `"processor"`, `graph.compile()` -> `app`
  - Invoke:
    - `answers = app.invoke(values=[1,2,3,4], name="Steve")`
    - `answers["result"]` -> `"Hi there Steve. Your sum is equal to 10"`

- Caveats and checks:
  - Use compiled graph handle: invoke on compiled object (e.g., `app.invoke`), not uncompiled `graph.invoke`.
  - If some state attributes are not provided on invocation, they may be initialised to `None`. Using `state["result"]` as a right-hand-side input without checking may cause problems. In the example it works because node assigns `state["result"]` (does not read it first).
  - Printing state before and after node execution helps visualize how state updates.

- Exercise (from transcript):
  - Create a graph that accepts `values`: list[int], `name`: str, and `operation`: either `'+'` or `'*'`. If `operation` is `'+'`, sum elements; if `'*'`, multiply elements. Do it inside a single node (use an if statement).

---

## Sequential graph (multiple nodes connected in sequence)

- Objective: create multiple nodes that process different parts of state in sequence; learn edges.

- State schema example:
  - `class AgentState(TypedDict):`
    - `name: str`
    - `age: str`
    - `final: str`

- Node examples:
  - `def first_node(state: AgentState) -> AgentState:`
    - Set part of `state["final"]`, e.g. `state["final"] = f"Hi {state['name']}."`
    - `return state`
  - `def second_node(state: AgentState) -> AgentState:`
    - Update `state["final"]` further:
      - Important caveat from transcript: do not overwrite previous `state["final"]` (will lose earlier content). Solution: concatenate:
        - `state["final"] = state["final"] + " You are " + state["age"] + " years old."`
    - `return state`

- Graph construction and adding edge:
  - `graph = StateGraph(state_schema=AgentState)`
  - `graph.add_node("first_node", action=first_node)`
  - `graph.add_node("second_node", action=second_node)`
  - Set entry point to `"first_node"`, finish point to `"second_node"`
  - Add directed edge connecting nodes:
    - `graph.edge.add_edge(start_key="first_node", end_key="second_node")`
  - `app = graph.compile()`
  - Invoke with `name` and `age`, final state shows concatenated message.

- Concept reinforced:
  - Any state attribute may be updated at any node; take care not to accidentally overwrite earlier content unless intended.

- Exercise (from transcript):
  - Build a three-node sequential graph that accepts `name`, `age`, and `skills` (list). Node 1 personalizes name greeting; Node 2 describes age; Node 3 formats skills list. Combine into `result` and output combined message. Hint: use `add_edge` twice.

---

## Conditional graph (routing by condition)

- Objective: implement conditional routing in the graph (edges chosen by condition).

- Imports alternative style:
  - The transcript shows a method importing `start` and `end` and using them to wire graph entry/exit.

- State schema example:
  - `class AgentState(TypedDict):`
    - `number1: int`
    - `operation: str`  (e.g., `"+"` or `"-"`)
    - `number2: int`
    - `final_number: int`

- Nodes:
  - `def adder(state: AgentState) -> AgentState:` sets `state["final_number"] = state["number1"] + state["number2"]`; return state.
  - `def subtractor(state: AgentState) -> AgentState:` sets `state["final_number"] = state["number1"] - state["number2"]`; return state.
  - `def decide_next_node(state: AgentState)` — this node picks which edge to return based on `state["operation"]`.
    - Important nuance: in Langraph the routing (router) node returns an edge identifier rather than the updated state. Because other nodes are written to accept and return state, the router must behave differently.
    - Example logic inside `decide_next_node`:
      - `if state["operation"] == "+": return "addition_operation"`
      - `elif state["operation"] == "-": return "subtraction_operation"`

- Lambda / pass-through fix:
  - Problem: `decide_next_node` returns an edge identifier instead of a `state`. When adding that node to the graph, the graph expects node actions to return `state`. To work around this, use a pass-through lambda for the router when adding it as a node:
    - Add node with action `lambda state: state` (or `lambda state: state` as a pass-through) so the node conforms to the expected signature.

- Graph construction with conditional edges:
  - Add nodes: router (source), add node, subtract node.
  - Set entry: connect `start` to router.
  - Add conditional edge:
    - Use `graph.add_conditional_edge(source="router", path=decide_next_node, path_map={ "addition_operation": "add_node", "subtraction_operation": "subtract_node" })`
      - `source` — router node name
      - `path` — the routing action (the function that returns an edge key)
      - `path_map` — map edge keys (returned by `path`) to node names to route to.
  - Add edges from add/subtract nodes to the end point:
    - `graph.edge.add_edge(start_key="add_node", end_key="end")`
    - `graph.edge.add_edge(start_key="subtract_node", end_key="end")`
  - `app = graph.compile()`
  - Example invocation:
    - Input: `number1=10, operation='-', number2=5` -> `final_number` becomes `5`.

- Caveats explained:
  - Router returns edge identifiers, not state — must be handled appropriately.
  - Use `start` import to connect entry to router node in this construction approach.

- Exercise (from transcript):
  - Extend the pattern: handle two independent operations over four numbers (two separate add/subtract flows as a larger graph). This reinforces conditional edges.

---

## Looping graph (routing back to a node)

- Objective: implement looping logic by routing data back into a node using conditional edges.

- Graph design (from transcript example):
  - Start -> Greeting node -> Random node (loop) -> end
  - Random node is executed repeatedly (e.g., 5 times) generating random numbers appended to a list in state; loop controlled by a counter attribute in state.

- State schema example:
  - `class AgentState(TypedDict):`
    - `name: str`
    - `number: List[int]`
    - `counter: int`

- Greeting node:
  - `def greeting_node(state: AgentState) -> AgentState:`
    - Update `state["name"] = "hi there " + state["name"]`
    - Initialize `state["counter"] = 0` — robustness measure: set counter to zero regardless of user input to avoid rubbish start values.
    - `return state`

- Random node:
  - `def random_node(state: AgentState) -> AgentState:`
    - Generate a random integer between 0 and 10 (using Python `random`).
    - Append to `state["number"]` list.
    - Increment `state["counter"] += 1`
    - `return state`

- Router function for loop/exit:
  - `def should_continue(state: AgentState):`
    - If `state["counter"] < 5`: return `"loop"`
    - Else: return `"exit"`
  - `loop` and `exit` are edge identifiers mapped to the next node names.

- Graph wiring:
  - Add nodes `greeting_node` and `random_node`.
  - Add a directed edge from `greeting_node` to `random_node`.
  - Add conditional edge from source=`random_node`, path=`should_continue`, path_map mapping:
    - `"loop"` -> `"random_node"` (loop back)
    - `"exit"` -> `"end"`
  - Set entry to `greeting_node`. Compile.
  - Invoke — graph will execute random node until counter reaches 5, then exit.

- Notes and caveats:
  - Multiple implementation approaches exist for loops; this is one idiomatic Langraph approach using conditional edges.
  - Robustness measure: reinitializing counter inside greeting node ensures unwanted starting values are overridden.

- Exercise (from transcript):
  - Implement an automatic higher/lower guessing game:
    - Graph should autonomously guess a number between lower and upper bounds (1..20 by default) with max attempts 7.
    - No human-in-the-loop: graph must guess and use hint tool outputs ("higher"/"lower") to adjust bounds and continue guessing. State includes: player name, guessed list, attempts count, lower bound, upper bound; loop until correct guess or attempts exhausted.

---

# AI agents (Langraph-focused agent patterns and examples)

## Simple bot (LLM integration into a graph)

- Goal: integrate a Large Language Model (LLM) into a Langraph node and run a simple chatbot-like flow.

- Key imports and setup:
  - Use `HumanMessage` type from LangChain message objects.
  - Use `ChatOpenAI` from `langchain.chat_models` (OpenAI LLM wrapper).
  - Load environment variables for API keys via `load_env()`.

- State schema:
  - `class AgentState(TypedDict):`
    - `messages: List[HumanMessage]` — a list of human message objects because we will send human message objects to the LLM.

- LLM initialization:
  - `lm = ChatOpenAI(model_name="gpt-4o-mini")` (transcript uses GPT4o model as example; LangChain wrapper used)
  - Note: need API key in env for cloud calls.

- Node action (process):
  - `def process(state: AgentState) -> AgentState:`
    - `response = lm.invoke(inputs=state["messages"])` — invoke model with the list of messages.
    - Print or inspect `response` and return `state`.
  - Graph:
    - Add node `process` to `graph`, entry->process->end, compile.

- Invocation / loop:
  - Terminal input loop: repeatedly read user input and send as messages.
  - The simple bot does not persist memory across restarts — state is in-memory.

- Limitations:
  - No persistent memory: after exiting the program, state is lost.
  - This is essentially an LLM wrapper within a graph node — not yet an agent with memory.

---

## Chatbot with persistent conversation history (memory)

- Objective: create a chatbot that keeps full conversation history in the state (human + AI messages) and persists it to disk to survive process restarts.

- Key additions:
  - Import `AIMessage` and `Union` to allow `messages` to contain both human and AI messages.
  - Use `Union[HumanMessage, AIMessage]` as element type for `messages`.

- State schema:
  - `class AgentState(TypedDict):`
    - `messages: List[Union[HumanMessage, AIMessage]]`

- Node action:
  - `def process(state: AgentState) -> AgentState:`
    - `response = lm.invoke(inputs=state["messages"])`
    - Append the AI response as `AIMessage(content=response.content)` into `state["messages"]`.
    - Return `state`.

- Conversation loop:
  - On each user input:
    - Append `HumanMessage(content=user_input)` to the `conversation_history` (same as `state["messages"]`).
    - Invoke agent (compiled graph).
    - After response, optionally write `conversation_history` to disk for persistence.

- Persistence solution described:
  - Problem: state in memory is erased when the program exits.
  - Simple practical solution shown: write full conversation (both human and AI messages) to a text file (e.g., `log.txt`) after the session. For each message, write whether it came from user or AI and the content.
    - The transcript code checks message type (`isinstance`) and writes accordingly.
  - After restarting process, without reading the log back into state, the program does not remember the previous conversation (demonstration given).
  - Additional note from transcript: more robust solutions include saving to a database or vector DB (not implemented in the transcript), but for quick prototyping the text file approach was used.

- Token growth issue:
  - Problem: conversation history simply keeps growing and increases LLM token usage (cost).
  - Practical mitigation suggested in transcript:
    - Trim old messages (e.g., if number of messages exceeds some threshold like 5, remove oldest messages) — keep recent messages because they are most relevant.
  - This advice came from the speaker as a pragmatic approach to reduce cost.

- Example behavior observed:
  - While program runs, chatbot retains memory (e.g., user introduced themselves as "Steve"; the bot later knows the name).
  - After program restart (without persisting state back into the running state), the chatbot no longer knows that identity until the log is loaded again.

---

## React agent (REAct — Reasoning + Acting)

- Concept: an agent architecture that alternates between reasoning (LLM deciding next action) and acting (invoking tools). The agent loops, calling tools as needed until no more tool calls are required, then returns a final answer.

- Key type annotations discussed:
  - `Annotated`, `Sequence`, `TypeDict`:
    - `Annotated` provides metadata/extra context for a type (e.g., to describe constraints without affecting the base type).
    - `Sequence` is a typing helper for sequences (useful to handle message lists).
  - Reducer function:
    - `add_messages` from `langraph.dosage` is used as a reducer function: it controls how node updates merge with existing state. Without a reducer, new updates would overwrite the existing value. `add_messages` appends messages to a chat history rather than overwriting.

- Tools:
  - Define tools via decorator `@tool`.
  - Each tool must have a docstring describing its purpose — docstrings are required for tools (they tell the LLM what the tool does).
  - Example tool: addition tool
    - `@tool`
      `def add(a: int, b: int) -> int:`
        `"""Adds two numbers"""` (docstring required)
        `return a + b`
  - Bind tools to model: `model.bind_tools(tools)` makes the list of tools available to the model/agent.

- State schema for REAct:
  - `class AgentState(TypedDict):`
    - `messages: Annotated[Sequence[BaseMessage], reducer=add_messages]`
    - (Sequence + reducer ensures append behavior and avoids manual list manipulation in nodes.)

- LLM node (the agent):
  - `def model_call(state: AgentState) -> AgentState:`
    - Compose `system` message (system prompt), include `state["messages"]`.
    - Invoke model: `response = model.invoke(...)`
    - Update `state["messages"]` using the reducer mechanism so new response is appended.
    - Return `state`.

- Tool node:
  - A `tool_node` wraps tool execution; the graph structure has a `tool_node` that receives tool calls from the agent and executes them.

- Conditional edge:
  - `should_continue(state)` determines whether to continue (call tools) or end.
  - Graph wiring:
    - Start -> agent node (`R_agent`).
    - Conditional edge from `R_agent`:
      - If `continue` -> go to `tool_node`.
      - If `end` -> go to `end`.
    - Edge from `tool_node` back to `R_agent` (the loop), so after tool execution result is passed back to the LLM (agent) for reasoning and deciding next step.
  - Example run:
    - Input: `"add 3 + 4"` -> agent decides which tool to call (add), calls it; the tool returns `7`; the agent receives tool output, composes final answer, and returns it.
    - The LLM decides tool arguments and which tool(s) to call.
    - Tools must have docstrings or the graph will error.

- Caveats and practical notes:
  - Docstrings on tools are required — if missing, errors occur (tools must be described).
  - The LLM determines tool arguments from the messages; tools should accept and validate arguments.
  - Tools allow the agent to perform operations that are external to the LLM's internal knowledge (e.g., precise math).
  - The agent can call multiple tools sequentially (e.g., add, then multiply) in one session — the graph loop supports repeated tool calls.
  - Examples shown: add, subtract, multiply tools; compound instruction (add then multiply) executed across tool calls.

---

## Drafter project (human-AI collaborative document drafting)

- Project goals (requirements encoded in transcript):
  - Speed up drafting documents and emails.
  - Provide human-AI collaboration: human gives continuous feedback, agent stops when human is happy.
  - Be able to save drafts to disk.

- Implementation design decisions:
  - Two tools: `update` (modify document content) and `save` (save current document to text file and finish).
  - Tool behavior:
    - `update(content: str)`: updates the current document with provided content and returns a confirmation message.
    - `save(file_name: str)`: ensure `.txt` extension, write `document_content` to disk, return confirmation that document saved and process finished.
  - Global variable usage:
    - Use a global variable `document_content` as shared storage to let tools access and modify the current document.
    - Rationale: the proper injected state mechanism in Langraph is beyond the scope of the course; global variable serves as a practical workaround for tools to see and update document content in this example.

- Agent behavior (`r_agent` node):
  - System prompt defines the agent as "Drafter — a helpful writing assistant." Instructions include:
    - Use `update` tool to modify document with provided instructions.
    - Use `save` tool to save the document and finish when requested.
    - Always show current document after modifications.
  - Interaction flow:
    - If state messages is empty: agent asks what the user would like to create.
    - Else: agent prints current document content (so user can review) and asks what to do next.
    - User reply is passed into the graph; the agent may call `update` or `save` accordingly.
  - Output: prints AI response and any tool result messages to the terminal.

- Graph wiring:
  - Nodes: `agent` node (the LLM agent) and `tool_node` (containing update and save tools).
  - Edge: agent -> tool_node (agent may call tools).
  - Conditional edge from tool_node: if the last tool called was save -> route to `end`; if update -> route to `continue` (loop back to agent).
  - Compile graph.

- Run example:
  - User asks to create an email to Tom; agent produces draft and uses `update` tool to change content; user requests further edits; when satisfied user issues `save` command; `save` tool writes file to disk with generated file name (agent may generate the file name).
  - The process demonstrates human + AI iterative collaboration.

- Notes:
  - Use of a global variable is a practical compromise for the course example. The transcript mentions injected state as a Langraph feature for a “proper” approach but it is beyond the course scope.
  - Agent generated file names are acceptable (agent can produce a suitable file name; code ensures `.txt` suffix).

- Extensions mentioned by transcript:
  - Add voice features (speech-to-text/text-to-speech) or GUI, connect to knowledge base, or other improvements (presented as possible extensions for learners).

---

## Retrieval-Augmented Generation (RAG) agent

- Objective: build a RAG pipeline combining document loader, chunking, embeddings, vector DB (Chroma), retriever tool, an LLM agent and a retriever agent to execute tool calls. The graph uses conditional looping and answers questions grounded in a document.

- Key steps and explanations:

1. Environment and model
   - Load environment variables for API keys.
   - Initialize LLM with `temperature=0` for deterministic outputs (transcript explanation: temperature controls stochasticity; zero makes outputs more deterministic).

2. Embeddings and document source
   - Initialize embedding model (must be compatible with chosen LLM).
   - Example source: a PDF “stock market performance 2024” with nine pages loaded via a PDF loader (PI PDF loader in transcript).
   - Check that loader successfully loads pages.

3. Chunking
   - Use `RecursiveCharacterTextSplitter` with parameters:
     - `chunk_size = 1000` (tokens)
     - `chunk_overlap = 200`
   - Explanation:
     - `chunk_size`: when reached, start a new chunk.
     - `chunk_overlap`: consecutive chunks share some tokens (200) so content continuity is preserved.

4. Vector store (Chroma)
   - Create Chroma vector database with embeddings for chunks and store them in a local directory with collection name (e.g., `"stock_market"`).
   - If collection does not exist, create and populate it.
   - Example: printing that the Chroma DB created or loaded.

5. Retriever
   - Create retriever from vector store: `retriever = vector_store.as_retriever(search_type="similarity", k=5)`
     - `k` parameter: number of top similar chunks to return (transcript used `k=5`).
   - Retriever will be used by the tool to fetch the most relevant chunks.

6. Retriever tool
   - Decorated with `@tool`, accepts `query: str`.
   - Implementation:
     - Call `retriever.get_relevant_documents(query)`
     - If no relevant documents: return a message indicating no relevant information found.
     - Else: collect content from returned documents and return them (tool message content).
   - Purpose: provide local-document-grounded context back to LLM.

7. LLM and tools binding
   - Bind the `retriever_tool` to the model: `model.bind_tools([retriever_tool])` (so the model can decide to call retriever).

8. Message schema and reducer
   - Use `messages` state as annotated sequence of `BaseMessage` plus `add_messages` reducer (same pattern as REAct).
   - This makes message appends handled by reducer rather than manual list manipulation.

9. Agent nodes:
   - `llm_agent` node: calls LLM with system instructions and state messages; system prompt instructs LLM to answer questions about the loaded document, to cite document parts used in answers (to reduce hallucination).
   - `retriever_agent` node: examines last LLM response for tool calls; if retriever tool requested, invoke it and return tool output to state; handles invalid tool names with an error message.

10. Conditional flow:
    - After `llm_agent`, use `should_continue` to check whether LLM issued a tool call:
      - If yes: route to `retriever_agent` (tool execution).
      - If no: route to `end`.
    - Retriever returns tool output; flow loops back to `llm_agent` with retrieved content included, allowing LLM to use retrieved text to answer and cite relevant parts.

11. Compile graph and interactive loop:
    - Compile `app = graph.compile()` (saved as e.g., `rag_app`).
    - Provide interactive loop: read user question, invoke `app.invoke(query=...)` repeatedly until `exit` or `quit`.
    - Observed behavior:
      - Asking document-relevant question (e.g., S&P 500 performance) triggers retriever tool, returns relevant chunks, LLM answers and cites parts.
      - Asking about content not present in the document returns "no relevant information in document" — reduces hallucination risk.

- Parameters and caveats highlighted:
  - Temperature set to 0 for deterministic model outputs.
  - Embedding model and LLM should be compatible (dimension or other compatibility issues).
  - Chunking parameters (`chunk_size`, `chunk_overlap`) influence retrieval granularity.
  - `k` in retriever determines how many chunks are returned (trade-off between more context vs. token cost).
  - System prompt instructs the LLM to cite document parts to reduce hallucination.

---

# Course artifacts and pedagogical notes (as presented)

- The course contains exercises for each graph; answers are available on GitHub (speaker indicated).
- Speaker emphasis:
  - Form good habits early: docstrings for nodes/tools, typed state schemas, print debugging, compile vs runtime logic errors.
  - Start simple and iterate: initial graphs are intentionally basic to build foundations before adding agents, tools, loops, conditional logic.
  - Multiple ways to build graphs exist — the lecture presented one workable approach for each concept.
- Closing note: After completing graphs and agents in the course, learners are ready to design agentic systems and scale up (speaker invites contact for questions).
