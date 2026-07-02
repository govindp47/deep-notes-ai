# Langraph Course — Structured Study Notes (from transcript)

Course overview

- Instructor: Vbeca (Vava), robotics and AI student.
- Goal: Teach fundamentals of Langraph — how to design, implement, and manage graph-based conversational AI workflows in Python using Langraph (built on LangChain).
- Target audience: People who have heard of Langraph but never coded in it.
- Course approach: Step-by-step, beginner-friendly, detailed; theoretical sections followed by coding exercises. Answers available on GitHub.

---

## Section 1 — Type annotations (brief theory)

Purpose

- These annotations appear heavily in Langraph code. Short, practical overview to prepare for later coding.

Contents

- Dictionaries
  - Python dict example: movie = {"name": "Avengers Endgame", "year": 2019}
  - Problem: plain dicts do not enforce structure or types; can cause runtime/logical errors in large projects.
- Typed dictionaries (TypedDict)
  - Solution: define schema as a class (TypedDict).
  - Example pattern:
    - class Movie(TypedDict): name: str; year: int
    - movie: Movie = {"name": "Avengers Endgame", "year": 2019}
  - Benefits: type safety (reduces runtime errors) and improved readability/debuggability.
  - Note: TypedDicts are used extensively in Langraph for defining states.

- Union
  - Purpose: specify that a value may be one of several types.
  - Example: def square(x: Union[int, float]) -> float: ...
  - Effect: allows either int or float inputs; rejects other types (e.g., string).
  - Usage in Langraph: used extensively to provide type hints and catch incorrect usage.

- Optional
  - Similar to Union with None included.
  - Example: Optional[str] means the value can be str or None.
  - Example function: nice_message(name: Optional[str]):
    - If name provided, use it; if None, handle as “random person”.
  - Important: Optional restricts to specified types plus None only.

- Any
  - Means “this value can be any type.”
  - Example: def print_value(x: Any): print(x)

- Lambda functions
  - Short functions used inline, often with map or similar.
  - Example: nums = [1,2,3,4]; squares = list(map(lambda x: x*x, nums)) -> [1,4,9,16]
  - Purpose: conciseness and efficiency for small anonymous functions.

Closing note

- These are overview items — not required to memorize, but useful to recognize in code.

---

## Section 2 — Core Langraph elements (theoretical)

High-level description

- Langraph composes workflows as directed graphs where nodes perform operations and a shared state flows between them.

Elements and relationships

1. State
   - Definition: shared data structure holding current application information/context — the “application memory”.
   - Role: nodes read and modify state as they execute.
   - Analogy: a meeting-room whiteboard where participants (nodes) write and update shared info.

2. Node
   - Definition: individual function or operation performing a specific task.
   - Input: typically the current state.
   - Output: updated state.
   - Analogy: an assembly-line station that does one job (attach part, paint, inspect).

3. Graph
   - Definition: overarching structure mapping nodes and execution flow; shows sequence and conditional routing.
   - Analogy: a road map connecting cities and intersections (choices).
   - Name significance: “graph” is central to Langraph.

4. Edges
   - Definition: connections between nodes that determine flow of execution.
   - Types:
     - Standard (directed) edges: specify next node.
       - Analogy: train track connecting stations; state is the train that moves and is updated.
     - Conditional edges: route execution based on condition applied to current state.
       - Analogy: traffic light (green/red/yellow selecting next path); similar to if/else statements.

5. Start point (start node)
   - Virtual entry point marking where graph execution begins.
   - Does not perform operations.
   - Analogy: starting line of a race.

6. End point (finish node)
   - Marks conclusion of the workflow; execution stops when reached.
   - Analogy: finish line.

7. Tools
   - Definition: specialized functions/utilities nodes can use (e.g., fetch API).
   - Distinction:
     - Node: part of graph structure that receives state and updates state.
     - Tool: functionality used inside nodes.
   - Analogy: tools in a toolbox (hammer, screwdriver).

8. Tool node
   - Special node whose main job is to run a tool and connect the tool’s output back into the state.
   - Analogy: operator (tool node) controlling a machine (tool) on an assembly line.

9. StateGraph (the State Graph)
   - Definition: framework to build and compile the graph structure; manages nodes, edges, state and overall flow.
   - Analogy: building blueprint describing design and connections.

10. Runnable
    - Definition: standardized executable component within AI workflow.
    - Difference to node:
      - Runnable: represents various operations; building block like a Lego brick.
      - Node in Langraph: typically receives the state, performs an action, updates state.
    - Analogy: Lego brick snapped together to build complex structures.

11. Message types (commonly used)
    - HumanMessage: input from a user (human).
    - AIMessage: responses generated by AI models.
    - SystemMessage: provides instructions or context to the model (e.g., “You are a helpful assistant”).
    - ToolMessage: used for tool usage outputs (similar to function message).
    - FunctionMessage: represents a function call/tool call.

Closing note

- Many of these will become concrete when coding graphs and agents.

---

## Section 3 — Coding in Langraph (practical)

Overview

- Start with small graphs, then progress to agents.
- Focus in early graphs: learn syntax, state flow, nodes, edges, conditional routing, loops, and compile/invoke lifecycle.

General coding patterns (recurring)

- State schema defined as TypedDict class (agent state).
- Node functions are standard Python functions that accept state (agent state) and return state.
- Docstrings in node functions are important (they describe the function’s purpose; docstrings are required for tools to describe them to LLMs).
- Build graph with StateGraph( state_schema=AgentState ).
- Add nodes via graph.add_node(name, action=function).
- Set entry/finish via graph.set_entry_point(key) and graph.set_finish_point(key) — or use start/end imported objects in alternative approach.
- Add directed edges via graph.edge.add_edge(start_key, end_key).
- Add conditional edges via graph.add_conditional_edge(source, path, path_map).
- Compile graph via graph.compile() -> compiled app.
- Invoke via compiled_app.invoke(state_payload) and inspect outputs.
- Important cautions:
  - Compilation success does not guarantee correct runtime logic.
  - Docstrings are required for tools used by LLMs.
  - Be mindful of state fields that may be None if not provided as inputs.

Exercises

- Exercises accompany each graph in the course; answers available on GitHub.

---

## Graph 1 — Hello World Graph (single node)

Objectives

- Define agent state structure.
- Create a simple node that updates state.
- Build, compile, invoke graph.
- Understand how data flows through a single node.

Implementation pattern (conceptual)

1. Imports:
   - TypedDict, dict, StateGraph (from Langraph).
2. Agent state:
   - class AgentState(TypedDict): message: str
3. Node function:
   - def greeting_node(state: AgentState) -> AgentState:
     - Docstring describing function: "Simple node that adds a greeting message to the state."
     - Update state.message: state["message"] = "hey " + state["message"] + " how is your day going"
     - return state
   - Docstrings are important (explain function to LLMs later).
4. Graph:
   - graph = StateGraph(state_schema=AgentState)
   - graph.add_node("greeter", greeting_node)
   - graph.set_entry_point("greeter")
   - graph.set_finish_point("greeter")
   - app = graph.compile()
5. Invoke:
   - result = app.invoke({"message": "Bob"})
   - Access result["message"] -> "hey Bob how is your day going"

Notes/warnings

- Compiles without errors, but may have logical runtime errors in more complex graphs.

Exercise for this graph

- Implement a personalized compliment agent:
  - Input: name (e.g., "Bob")
  - Output: "Bob, you're doing an amazing job learning Langraph."
  - Hint: concatenate the state value rather than replacing it.

---

## Graph 2 — Multiple inputs and list processing

Objectives

- Create more complex agent state with multiple fields (different types).
- Process list data inside a node.
- Invoke graph with structured inputs and retrieve outputs.
- Main goal: how to handle multiple inputs.

Implementation pattern

1. Imports:
   - TypedDict, List, StateGraph.
2. Agent state:
   - class AgentState(TypedDict):
     - values: List[int]
     - name: str
     - result: str
3. Node function:
   - def process_values(state: AgentState) -> AgentState:
     - Docstring: "Process handles multiple different value in multiple different inputs."
     - state["result"] = f"Hi there {state['name']}. Your sum is equal to {sum(state['values'])}"
     - return state
4. Graph:
   - graph = StateGraph(state_schema=AgentState)
   - graph.add_node("processor", process_values)
   - graph.set_entry_point("processor")
   - graph.set_finish_point("processor")
   - app = graph.compile()
5. Invoke:
   - answers = app.invoke({"values": [1,2,3,4], "name": "Steve"})
   - answers -> values, name, result -> "Hi there Steve. Your sum is equal to 10"
   - Access only result: answers["result"]

Important caution

- If you do not pass a field (e.g., result) on invoke, the field may be initialized as None. If your code reads an uninitialized field, it can cause errors. In the provided example the code only assigns state["result"], not reads it before assignment, so it works.

Debugging tip

- Place print statements before and after state update to see how the state changes.

Exercise

- Create a graph that receives:
  - name, values (list of integers), and operation (either "+" or "times").
  - Single node: if operation is "+", sum the elements; if "times", multiply all elements.
  - Output example: "Hi Jack Sparrow, your answer is 24" for multiplication on [1,2,3,4].
  - Hint: use an if statement in the node.

---

## Graph 3 — Sequential graph (multiple nodes, directed edges)

Objectives

- Create multiple nodes that sequentially process state.
- Connect nodes with directed edges.
- Learn to add edges: graph.edge.add_edge(start_key, end_key).
- Understand state updates flowing through sequence.

Implementation pattern

1. Agent state:
   - class AgentState(TypedDict):
     - name: str
     - age: str
     - final: str
   - (All strings in this example to keep simple.)
2. Node functions:
   - def first_node(state: AgentState) -> AgentState:
     - Docstring: "First node of our sequence."
     - state["final"] = f"Hi {state['name']}"
     - return state
   - def second_node(state: AgentState) -> AgentState:
     - Docstring: "Second node of sequence."
     - Important logical error example:
       - Incorrect: state["final"] = f"You are {state['age']} years old" (this would replace previous content)
       - Fix: concatenate: state["final"] = state["final"] + " " + f"You are {state['age']} years old"
     - return state
3. Graph:
   - graph = StateGraph(state_schema=AgentState)
   - graph.add_node("first_node", first_node)
   - graph.add_node("second_node", second_node)
   - graph.set_entry_point("first_node")
   - graph.edge.add_edge("first_node", "second_node")
   - graph.set_finish_point("second_node")
   - app = graph.compile()
4. Invoke:
   - result = app.invoke({"name": "Charlie", "age": "20"})
   - result["final"] -> "Hi Charlie You are 20 years old"

Notes

- Key logical point: be careful when updating state keys to avoid unintentionally overwriting previous content; concatenate where appropriate.

Exercise

- Extend to three nodes in sequence:
  - Accepts: user name, age, list of skills.
  - Node 1: personalize the name field with a greeting.
  - Node 2: describe age.
  - Node 3: list skills in a formatted string.
  - Combine into a result field; example output:
    - "Linda, welcome to the system. You are 31 years old, and you have skills in Python, machine learning and Langraph."
  - Hint: use graph.edge.add_edge twice to connect nodes in sequence.

---

## Graph 4 — Conditional graph (router node and conditional edges)

Objectives

- Implement conditional logic at graph-level to route state to different nodes.
- Use start and end imports for alternate entry/exit approach.
- Build router node that returns an edge name based on state.

Setup

- State:
  - class AgentState(TypedDict):
    - number_one: int
    - operation: str  # plus or minus
    - number_two: int
    - final_number: int

Nodes

- Add node:
  - def adder(state: AgentState) -> AgentState:
    - state["final_number"] = state["number_one"] + state["number_two"]
    - return state
- Subtract node:
  - def subtractor(state: AgentState) -> AgentState:
    - state["final_number"] = state["number_one"] - state["number_two"]
    - return state
- Router node (decide next node):
  - def decide_next_node(state: AgentState):
    - if state["operation"] == "+":
      - return "addition_operation"  # edge name
    - elif state["operation"] == "-":
      - return "subtraction_operation"
    - Note: This node returns the edge name, not the state.

Important subtlety and fix

- Problem: add_node expects nodes to return state. Router returns an edge name (not state), so graph.add_node("router", decide_next_node) would fail at compile/runtime.
- Fix: wrap as runnable that passes state through, e.g. use a lambda passthrough when adding the node:
  - graph.add_node("router", lambda state: state)
  - Then use graph.add_conditional_edge( source="router", path=decide_next_node, path_map={ "addition_operation": "add_node", "subtraction_operation": "subtract_node" } )
  - Explanation: the lambda is a pass-through runnable because the router is not changing the state but deciding the path. Comparison vs assignment difference noted.

Graph building (alternate style with start/end)

1. graph = StateGraph(AgentState)
2. graph.add_node("router", lambda state: state)
3. graph.edge.add_edge( start="start", end="router" )
4. graph.add_conditional_edge(
   - source="router",
   - path=decide_next_node,
   - path_map={ "addition_operation": "add_node", "subtraction_operation": "subtract_node" }
   )
5. graph.edge.add_edge("add_node", "end")
6. graph.edge.add_edge("subtract_node", "end")
7. app = graph.compile()

Invoke example

- app.invoke({"number_one": 10, "operation": "-", "number_two": 5}) -> final_number=5

Exercise

- Expand the conditional system to handle two separate operations in parallel:
  - Input four numbers and two operations.
  - Replicate the conditional-with-router pattern twice (one for first pair and one for second pair).
  - Output both final results (e.g., for 10-5 and 7+2 -> results 5 and 9).
  - Purpose: solidify conditional edge understanding.

---

## Graph 5 — Looping graph (returning edges)

Objectives

- Implement looping logic in a Langraph graph.
- Create nodes and a conditional edge that can route back to the same node (loop) or to end.
- Demonstrate a counter-based loop generating multiple outputs.

Design (desired graph)

- Nodes: greeting_node -> random_node
- random_node loops back to itself via a conditional edge while counter < 5
- After counter reaches 5, route to end node

State schema

- class AgentState(TypedDict):
  - name: str
  - numbers: List[int]
  - counter: int

Nodes

- greeting_node(state):
  - Purpose: set user name greeting and initialize counter to 0 to make the graph robust.
  - state["name"] = f"Hi there {state['name']}"
  - state["counter"] = 0  # reset/override user-supplied counter for robustness
  - return state
  - Why reset counter? Avoids unintended behavior if user passed negative or unexpected counters.
- random_node(state):
  - Generate a random number (0–10) and append to state["numbers"] list.
  - state["counter"] += 1
  - return state
- should_continue(state):
  - if state["counter"] < 5:
    - return "loop"  # edge name back to random node
  - else:
    - return "exit"  # edge name to end

Graph construction (conceptual)

1. graph = StateGraph(AgentState)
2. graph.add_node("greeting_node", greeting_node)
3. graph.add_node("random_node", random_node)
4. graph.edge.add_edge("greeting_node", "random_node")
5. graph.add_conditional_edge(
   - source="random_node",
   - path=should_continue,
   - path_map={ "loop": "random_node", "exit": "end" }
   )
6. graph.set_entry_point("greeting_node") or graph.edge.add_edge("start", "greeting_node")
7. graph.compile()

Example

- Invoke with {"name": "V", "numbers": [], "counter": -1}
- Because greeting_node resets counter to 0, random_node invoked 5 times, appending 5 random integers.
- Print statements inside random_node before & after the action can show the state evolution.

Exercise (looping/higher-lower game)

- Implement an automatic higher-or-lower guessing game with no human-in-the-loop for guesses:
  - Inputs: player name, guesses (empty list), attempts = 0, lower_bound = 1, upper_bound = 20
  - Graph must guess numbers automatically.
  - Max attempts: 7 (stop if correct or attempts reach 7).
  - Each guess produces a hint node output: “higher” or “lower”; graph must update bounds based on hints and produce next guess accordingly.
  - Goal: reinforce loop + conditional logic in Langraph.

---

## Section 4 — AI Agents (building agents that integrate LLMs and tools)

General notes

- Langraph builds on top of LangChain libraries; you will import LangChain message types and models (e.g., ChatOpenAI).
- Use env files to store API keys and configuration (load with load_env or similar).
- Docstrings are critical for tool descriptions (so LLMs know tool purpose).
- Practical pattern: create state, node that calls LLM via model.invoke(...), compile graph, invoke.

---

## Agent 1 — Simple bot (LLM integrated into a node)

Objectives

- Define state as a list of HumanMessage objects.
- Initialize ChatOpenAI model (speaker used "GPD4" / variants in transcript).
- Send messages to LLM using lm.invoke(state.messages).
- Build/compile graph and invoke it.
- Main goal: integrate LLM calls into graph nodes.

Implementation (conceptual)

1. Imports:
   - TypedDict, List
   - HumanMessage (from LangChain messages)
   - ChatOpenAI (from langchain.chat_openai)
   - StateGraph, env loader
2. State:
   - class AgentState(TypedDict):
     - messages: List[HumanMessage]
3. Model init:
   - lm = ChatOpenAI(model="gpt-4o" / "gpt-4" variants used in transcript)
   - Load API key from env.
4. Node process:
   - def process(state: AgentState) -> AgentState:
     - response = lm.invoke(state["messages"])
     - print(response.content)
     - return state
5. Graph:
   - graph.add_node("process", process)
   - graph.set_entry_point("process")
   - graph.set_finish_point("process")
   - app = graph.compile()
6. Run loop:
   - Ask user for input, append it to state messages as HumanMessage, invoke app.
   - Example outputs: “Hello, how can I assist you today?”, etc.

Limitations observed

- No persistent memory across program restarts because state is in-memory variables; after program exit, state is lost.
- Behavior: after restart, asking "What is my name?" returns "I don't have the ability to know your name" — because state was lost.

Quick solution shown in course

- Save conversation history to a text file:
  - Iterate conversation_history messages and write human vs AI content lines to a file.
  - Use this as a simple persistence method during prototyping.

Note on cost

- When conversation history grows large, token costs increase; suggested mitigation (course hint): trim older entries beyond a threshold (example: keep last 5 messages).

---

## Agent 2 — Chatbot with memory (human + AI messages)

Objectives

- Maintain full conversation history using both HumanMessage and AIMessage types.
- Use Union in state typing to allow both message types in one list.
- Initialize LLM, append responses as AIMessage, and preserve conversation during run.

Implementation (conceptual)

1. Imports:
   - HumanMessage, AIMessage, Union
2. State:
   - class AgentState(TypedDict):
     - messages: List[Union[HumanMessage, AIMessage]]
3. Model:
   - lm = ChatOpenAI(..., model="gpt-4" per transcript)
4. Node process:
   - def process(state: AgentState) -> AgentState:
     - response = lm.invoke(state["messages"])
     - state["messages"].append(AIMessage(content=response.content))
     - print(response.content)
     - return state
5. Execution loop pattern:
   - Initialize conversation_history = []
   - While user not typing exit:
     - Append HumanMessage(user_input) to conversation_history
     - app.invoke({"messages": conversation_history})
     - After invocation, update conversation_history = returned messages
   - This provides in-run memory: the LLM receives full conversation before each new invocation.

Problems & solutions

- Problem 1: No persistence after program exit (same as Agent 1).
  - Quick solution: write conversation_history to a text file on exit (course demonstrates writing conversation log).
- Problem 2: Conversation grows and token use (and cost) increases.
  - Suggested approach: prune older messages once history length exceeds threshold (e.g., if >5 messages, remove oldest). (This approach was suggested by the instructor.)

Debugging tip

- Print the state messages to view current conversation structure (shows HumanMessage/AIMessage entries and content).

---

## Agent 3 — React agent (Reasoning and Acting)

Purpose

- Create an agent that can “reason” (LLM decides) and “act” (call tools).
- Loop: agent can call a tool, tool returns content, agent receives the tool output and continues or stops.
- Typical use: LLM chooses tools when needed; stops when done.

Key concepts introduced

- Annotated and Sequence type annotations:
  - Annotated: attach metadata to a type (e.g., validation note on email).
  - Sequence: type annotation to indicate a sequence; useful to avoid manual list manipulations.
- add_messages reducer:
  - A reducer function controlling how updates are combined with existing state.
  - add_messages appends messages to existing state rather than overwriting.
  - Purpose: allow aggregation of messages (preserve history) automatically.

Implementation pattern (conceptual)

1. Imports:
   - Annotated, Sequence, TypedDict
   - base message types (BaseMessage, ToolMessage, SystemMessage)
   - add_messages reducer (from langraph.dosage in transcript)
   - tool decorator, tool node constructs
   - ChatOpenAI
2. State:
   - class AgentState(TypedDict):
     - messages: Annotated[Sequence[BaseMessage], add_messages]  # sequence with reducer
3. Tools (decorated functions):
   - @tool
     def add(a: int, b: int) -> int:
       """Add two numbers"""
       return a + b
   - (Also subtract, multiply examples added later)
   - Docstrings are mandatory (tool description for LLM).
4. Bind tools to model:
   - model = ChatOpenAI(model="gpt-4...")  # as in transcript
   - model.bind_tools([add, subtract, multiply])  # allows model to call these tools
5. Agent node
   - def model_call(state: AgentState) -> AgentState:
     - Prepare messages including SystemMessage for instructions
     - Invoke model: response = model.invoke(state["messages"] + [HumanMessage(query)])
     - Return updated state messages (add_messages reducer handles appending)
6. should_continue for conditional edge:
   - Checks whether last model response contains tool calls (tool name) and returns True/False for conditional edge routing.
7. Graph structure:
   - graph.add_node("r_agent", model_call)
   - graph.add_node("tools", tool_node(tools))
   - graph.set_entry_point("r_agent")
   - graph.add_conditional_edge(source="r_agent", path=should_continue, path_map={True: "tools", False: "end"})
   - graph.edge.add_edge("tools", "r_agent")  # return back to agent after tool runs
   - app = graph.compile()

Behavior demonstrated

- LLM decides to use the 'add' tool for math queries.
- The tooling loop can run multiple times (e.g., multiple tool calls in one session).
- If no tool call is necessary (e.g., request a joke), LLM may answer directly without tools.

Important notes

- Docstrings for tool functions are required (tools must include a description).
- The LLM determines which tool to call and what arguments to provide.
- Tools perform actual deterministic functions (e.g., exact arithmetic), so the app can avoid hallucinations for those tasks.

Examples

- add 3 + 4 -> model calls add tool, returns tool result 7, agent answers with final message.
- Complex chain: add 40 + 12 then multiply result by 6 -> model orchestrates two tool calls and returns final answer 312.

---

## Agent 4 — Drafter mini-project (human-AI collaborative drafting + save tool)

Project brief

- Build an AI agentic system ("Drafter") to speed up drafting documents and emails.
- Requirements:
  - Human-AI collaboration: human provides continuous feedback; AI updates draft accordingly.
  - Human can instruct “save” and the system should save draft and finish.
  - System should be able to save drafts.

Design overview

- Graph structure: start -> agent node -> tool node
- Tools: update (updates document content), save (save to text file and finish process)
- Special note: instructor used a global variable (document_content) to store content as a workaround for injected state which is beyond the course scope.

Implementation pattern (conceptual)

1. Global variable:
   - document_content = ""  # will be updated by update tool and read by save tool
   - Rationale: simple workaround for injected state in tools; course warns about injected state being beyond scope.
2. State:
   - class AgentState(TypedDict):
     - messages: Annotated[Sequence[BaseMessage], add_messages]
3. Tools:
   - @tool
     def update(content: str) -> str:
       - global document_content
       - document_content += content  # update global content
       - return "Document has been updated successfully. The current content is: {document_content}"
   - @tool
     def save(file_name: str) -> str:
       - ensure file_name ends with ".txt" (append if missing)
       - global document_content
       - open(file_name, "w") and write document_content
       - return "Saved to {file_name}" or include success message; if exception, return error message
4. Model binding:
   - model = ChatOpenAI(...)
   - model.bind_tools([update, save])
5. Agent function (r_agent):
   - If state messages empty:
     - Ask user what they want to create
     - Append user input as HumanMessage
   - Else:
     - print current document to user
     - ask what to do with the document (update/save)
     - collect user input (HumanMessage)
   - Combine system message + state messages + user message, invoke model
   - Print model response and any tool messages returned
   - Return updated state messages
6. should_continue function:
   - Inspect latest tool message; if save tool used -> return "end"; if update tool used -> return "continue"
7. Graph:
   - graph.add_node("agent", r_agent)
   - graph.add_node("tools", tool_node(tools))
   - graph.edge.add_edge("agent", "tools")
   - graph.add_conditional_edge(source="tools", path=should_continue, path_map={"continue": "agent", "end": "end"})
   - graph.set_entry_point("agent")
   - app = graph.compile()

Runtime behavior and demonstration

- User: “Write an email to Tom saying I cannot make it to the meeting.”
- Agent proposes email; user gives feedback and additional info; update tool used multiple times to append modifications.
- When user says “save it”, save tool runs, writes draft to a .txt file, and graph ends.
- The system auto-generates a file name if needed.
- Human-AI collaboration is achieved through the loop: agent -> tools -> agent until save triggers end.

Notes and caveats

- Global variable workaround used in course; proper approach involves injected state (out of scope).
- The app is prototyping-level but demonstrates the human-in-the-loop workflow.
- Extensions suggested by instructor (course mentions):
  - Add voice features: speech-to-text (e.g., OpenAI Whisper) and text-to-speech (e.g., ElevenLabs).
  - Add GUI or integrate a knowledge base or other enhancements.

---

## Agent 5 — Retrieval-Augmented Generation (RAG agent)

Purpose

- Demonstrate RAG workflow: retrieve relevant document chunks and use LLM to answer queries with citations from retrieved content.
- Graph structure: LLM agent asks retriever agent/tool; retriever returns relevant chunks; LLM synthesizes answer and cites document parts; conditional edge handles tool calls.

Key steps and components described

1. Load env and initialize ChatOpenAI model:
   - model = ChatOpenAI(..., temperature=0)  # deterministic outputs preferred in course
2. Embeddings:
   - Instantiate an embedding model to convert text into vector embeddings (speaker noted embedding model must be compatible with chosen LLM).
3. PDF loading:
   - Use PyPDF loader (PdfLoader per transcript) to load a PDF document (example: "stock_market_performance_2024.pdf").
   - Confirm number of pages (example: 9 pages).
4. Chunking:
   - Use RecursiveCharacterTextSplitter with parameters:
     - chunk_size = 1000 (tokens)
     - chunk_overlap = 200
   - Result: split pages into chunks; overlap ensures context continuity between chunks.
5. Vector store creation (Chroma)
   - Use Chroma vector database to store vectors locally in a collection (e.g., "stock_market") with a local path for persistence.
   - If collection doesn't exist, create it and add embeddings for chunks.
6. Retriever
   - Create retriever from Chroma vector store:
     - retriever = collection.as_retriever(search_type="similarity", k=5)
     - k: number of chunks returned (chosen as 5 in course).
7. Retrieval tool (decorated):
   - @tool def retriever_tool(query: str) -> str:
     - Use retriever to search documents for query (top-k similarity).
     - If no relevant documents: return message indicating no relevant info found.
     - If relevant docs found: gather their content into a results string and return.
8. Tools binding:
   - Bind retriever tool to model: model.bind_tools([retriever_tool])
9. State and reducer:
   - class AgentState(TypedDict):
     - messages: Annotated[Sequence[BaseMessage], add_messages]
   - add_messages ensures updates append rather than overwrite.
10. Agent LLM function:
    - Build a SystemMessage instructing the model:
      - Example instructions: answer questions about the loaded document and always cite specific parts used in answers (to reduce hallucination).
    - Invoke model with state messages and system message and return updated messages.
11. Retriever agent function:
    - Parse latest model response; if it contains a tool call:
      - Call the retriever tool with the query,
      - Return the tool result appended to the state,
      - Else, reply with error message if tool name invalid.
12. Graph:
    - graph.add_node("llm_agent", llm_agent)
    - graph.add_node("retriever_agent", retriever_agent)
    - graph.set_entry_point("llm_agent")
    - graph.add_conditional_edge(source="llm_agent", path=should_continue, path_map={"some_tool_edge": "retriever_agent", "no_tool": "end"})
    - graph.compile()

Demonstration and outcomes

- Example: ask "How was the S&P 500 performing in 2024?"
  - The graph calls retriever tool, gets top chunks from the documents, returns relevant content to the LLM.
  - LLM synthesizes answer and cites relevant document parts.
  - Output example in transcript: total return approximations and references to “magnificent 7” and 23% quote that matched the loaded document.
- Example: ask about OpenAI stock performance:
  - If document contains no information, the retriever returns “no relevant information” and LLM acknowledges that (no hallucination).

Notes

- Chunk size/overlap and k (number of similar chunks) are tunable parameters.
- The course stresses verifying retrieval outputs and instructs LLM to cite documents to limit hallucination.

---

## Final course notes & recommendations (as in transcript)

- The course ends here; many more practical AI agents can be built combining the taught patterns.
- Instructor availability: contact via LinkedIn for further questions (transcript mentions linking).
- Practice advice:
  - Start with small graphs and gradually compose more advanced agents.
  - Use docstrings consistently for nodes and tools (required for LLM-tool interaction).
  - Print statements help debugging and understanding state transitions.
  - Persist conversation state when necessary (file or DB) to maintain memory between runs.
  - Be mindful of token costs when passing long conversation histories to LLMs; trim older messages where appropriate.

---

Appendix — Exercises summary (from course)

- Graph 1 exercise: personalized compliment agent (concatenate state).
- Graph 2 exercise: plus or multiply single-node operation based on operation string.
- Graph 3 exercise: three-node sequence formatting name/age/skills, combining outputs into a result; use add_edge twice.
- Graph 4 exercise: replicate conditional structure twice to handle two operation pairs and output two results.
- Graph 5 exercise: automated higher/lower game with no human-in-the-loop; guesses between provided bounds, max 7 attempts; update bounds per hint; inputs include player name, guesses list (initialized empty), attempts counter, lower/upper bounds.

End of notes.
