# Type annotations (short primer)
- Purpose: provide type safety and improve readability/debuggability in Python; heavily used in Langraph for defining states.

- Dictionary vs TypedDict
  - Plain dict example:
    - movie = {"name": "Avengers Endgame", "year": 2019}
    - Problem: no structural/type guarantees → runtime/logic errors at scale.
  - TypedDict (type dictionary)
    - Implement as a class that specifies the types of keys:
      - class Movie(TypedDict):
          name: str
          year: int
      - movie: Movie = {"name": "Avengers Endgame", "year": 2019}
    - Benefits: type safety, better readability, easier debugging.
    - In Langraph: TypedDicts are used extensively to define state schemas.

- Union
  - Declares that a value may be one of several types.
  - Example:
    - def square(x: Union[int, float]) -> Union[int, float]:
        return x * x
  - Useful to catch incorrect usage and for flexible APIs. Used heavily in LangChain/Langraph.

- Optional
  - Equivalent to Union[T, None].
  - Example:
    - def nice_message(name: Optional[str] = None) -> str:
        if name:
            return f"Hi there {name}"
        return "Hey random person"
  - Enforces that value is either of the given type or None.

- Any
  - Means the value can be any type. Example:
    - def print_value(v: Any) -> None: print(v)

- Lambda functions
  - Short inline functions useful with map/filter, e.g.:
    - nums = [1,2,3,4]; list(map(lambda x: x*x, nums))  # [1,4,9,16]
  - Concise for small transformations.

# Core Langraph elements (concepts & analogies)
- State
  - Shared data structure that holds the application's current context (application memory).
  - Analogy: whiteboard in a meeting where all participants (nodes) read/write the current context.

- Node
  - A function/operation that receives state, performs a specific task, and returns (or updates) state.
  - Analogy: an assembly line station performing one task.

- Graph
  - The structure that maps how nodes are connected and executed; represents the workflow.
  - Analogy: a road map showing routes and intersections.

- Edge
  - A directed connection between nodes which determines flow of execution.
  - Analogy: a train track connecting stations. The state is the train passing between nodes.

- Conditional edge
  - Specialized edge that chooses next node based on a condition evaluated against the state.
  - Analogy: traffic light or an if/else statement: condition decides the path.

- Start / End nodes
  - Start: virtual entry point; marks where execution begins.
  - End: marks workflow conclusion; execution stops.

- Tool
  - Standalone utility functions (e.g., API fetchers) nodes can use.
  - Analogy: tools in a toolbox (hammer, screwdriver).

- Tool node
  - A special node whose primary job is to run a tool and merge its output back into state.
  - Analogy: operator controlling a machine on the assembly line.

- StateGraph
  - Blueprint and manager for the graph structure: nodes, edges, state schema, compilation.
  - Analogy: building blueprint.

- Runnable
  - Standardized executable component; can be combined modularly (think Lego bricks).
  - Relationship to Node: runnable represents operations; a node in Langraph receives state, acts, returns state.

# Message types (common)
- HumanMessage: input from user.
- AIMessage: response from LLM.
- SystemMessage: instructions/context provided to the model (e.g., "you are a helpful assistant").
- ToolMessage: message returned by a tool (tool usage-specific).
- FunctionMessage: represents function/tool calls (used with some LLM APIs).
- These mirror common patterns in LLM APIs (OpenAI, etc.).

# Building graphs in Langraph — practical patterns and examples

General pattern when coding graphs:
1. Define a TypedDict state schema for the agent.
2. Implement node functions (input: state, output: state).
3. Create a StateGraph, add nodes, add edges (entry/finish), compile.
4. Invoke the compiled graph (app.invoke or similar) with structured inputs.
5. Inspect returned state (state attributes such as message/result).

---

## Example: Hello World graph (single node)
- Objective: learn state definition, node function, add node to graph, compile, invoke.
- Steps (conceptual):
  1. Imports: TypedDict, dict, StateGraph.
  2. Define state schema:
     - class AgentState(TypedDict):
         message: str
  3. Implement node:
     - def greeting_node(state: AgentState) -> AgentState:
         """Simple node that adds a greeting message to state."""
         state["message"] = f"hey {state['message']} how's your day going"
         return state
     - Note: Use docstrings — they help LLMs later when functions are exposed to LLMs.
  4. Create graph:
     - graph = StateGraph(state_schema=AgentState)
     - graph.add_node("greeter", greeting_node)
     - graph.set_entry_point("greeter")
     - graph.set_finish_point("greeter")
     - app = graph.compile()
  5. Invoke:
     - result = app.invoke(message="Bob")
     - Access: result["message"] -> "hey Bob how's your day going"
  6. Caveat: graph.compile succeeding does not guarantee logic is correct (only syntactic/structural compile).

- Exercise: build a personalized compliment agent that concatenates into state.message (do not replace).

---

## Graph 2: Multiple inputs (lists + string)
- Objective: define more complex TypedDict with mixed types; handle list processing inside a node.
- State schema:
  - class AgentState(TypedDict):
      values: List[int]
      name: str
      result: str
- Node:
  - def process_values(state: AgentState) -> AgentState:
      """Handles list of integers and a name; sums list and writes formatted result."""
      state["result"] = f"Hi there {state['name']}. Your sum is equal to {sum(state['values'])}"
      return state
- Graph build:
  - graph = StateGraph(state_schema=AgentState)
  - graph.add_node("processor", process_values)
  - graph.set_entry_point("processor")
  - graph.set_finish_point("processor")
  - app = graph.compile()
- Invocation/example:
  - answers = app.invoke(values=[1,2,3,4], name="Steve")
  - answers["result"] -> "Hi there Steve. Your sum is equal to 10"
- Note: If you compile into app, invoke the compiled app (app.invoke), not graph.invoke.
- Debug tip: print state before/after node to visualize state mutation.
- Caution: if you didn't pass an optional state attribute (result) as input, it will be initialized as None; avoid reading None before assignment.

- Exercise: single node that accepts list of integers + name + operation ("+" or "*") and computes sum/product and formats result.

---

## Graph 3: Sequential graph (multiple nodes + edges)
- Objective: learn chaining nodes with directed edges; avoid accidental overwrites of state attributes.
- State schema:
  - class AgentState(TypedDict):
      name: str
      age: str
      final: str
- Nodes:
  - def first_node(state: AgentState) -> AgentState:
      """Personalize the greeting and initialize final."""
      state["final"] = f"Hi {state['name']}."
      return state
  - def second_node(state: AgentState) -> AgentState:
      """Append age information to final."""
      # Bug: replacing final instead of concatenating -> fixes by concatenation
      state["final"] = state["final"] + f" You are {state['age']} years old."
      return state
- Graph:
  - graph = StateGraph(state_schema=AgentState)
  - graph.add_node("first_node", first_node)
  - graph.add_node("second_node", second_node)
  - graph.set_entry_point("first_node")
  - graph.add_edge("first_node", "second_node")
  - graph.set_finish_point("second_node")
  - app = graph.compile()
- Example invoke with name="Charlie", age="20" → "Hi Charlie. You are 20 years old."
- Pitfall: state attributes can be overwritten when nodes update the same key; prefer concatenation if both pieces needed.
- Exercise: build three sequential nodes: greeting (name), age description, formatted skills list; combine into final result string.

---

## Graph 4: Conditional graph (router node + conditional edges)
- Objective: route execution to different nodes based on state (operation selection).
- State schema:
  - class AgentState(TypedDict):
      number1: int
      operation: str  # "+" or "-"
      number2: int
      final_number: int
- Nodes:
  - def adder(state: AgentState) -> AgentState:
      state["final_number"] = state["number1"] + state["number2"]
      return state
  - def subtractor(state: AgentState) -> AgentState:
      state["final_number"] = state["number1"] - state["number2"]
      return state
  - def decide_next_node(state: AgentState):
      """Router — returns the edge name to follow next based on state['operation']."""
      if state["operation"] == "+":
          return "addition_operation"
      return "subtraction_operation"
- Important Langraph nuance:
  - Router node often returns an edge name rather than a state object; but nodes are expected to return state normally.
  - If a node does not change state but needs to exist for routing, provide a passthrough such as:
    - lambda state: state   (a no-op that returns the state)
- Conditional edges:
  - graph.add_conditional_edge(
      source="router",
      path=decide_next_node,
      path_map={
        "addition_operation": ("add_node",),
        "subtraction_operation": ("subtract_node",)
      }
    )
  - (Edge names map to target nodes)
- Full graph:
  - Set start->router; router uses conditional edges to route to add/subtract nodes; add/subtract connect to end.
- Example: number1=10, operation="-", number2=5 → final_number=5.
- Exercise: extend to compute two separate pairs using two routers (two independent conditional flows) and output both results.

---

## Graph 5: Looping graph (conditional loop back)
- Objective: implement loop in graph by routing back to a node until a counter condition is met.
- Design shown: start -> greeting -> random_node -> (loop back to random_node) x 5 -> end
- State schema:
  - class AgentState(TypedDict):
      name: str
      numbers: List[int]
      counter: int
- Nodes & behavior:
  - greeting_node:
    - Set state["name"] = f"Hi there {state['name']}"
    - Initialize state["counter"] = 0  # sanitize user input to ensure robust loop start
  - random_node:
    - Append a random integer (0..10) to state["numbers"]
    - Increment state["counter"] += 1
    - return state
  - should_continue (router function):
    - if state["counter"] < 5:
        print debug
        return "loop"
      else:
        return "exit"
- Conditional edge mapping:
  - graph.add_conditional_edge(
      source="random_node",
      path=should_continue,
      path_map={
        "loop": ("random_node",),
        "exit": ("end",)
      }
    )
- Notes:
  - Setting counter to zero in greeting node prevents unintentionally long loops if user passes a negative initial counter.
  - This pattern demonstrates looping via conditional edges rather than in-node for-loops (intentionally pedagogical).
- Example invocation: initialized counter = -1 -> greeting sanitizes to 0 -> random_node loops 5 times -> exit to end.
- Exercise: implement an autonomous higher/lower guessing game:
  - Graph should guess numbers between lower/upper bounds (1..20 default), make up to 7 attempts, and adjust bounds after each hint ("higher"/"lower") until correct or max attempts reached. All guessing is automated (no human-in-loop).

# AI agents — moving from graphs to LLM integration

General notes:
- Langraph builds on LangChain; use LangChain's chat model wrappers (e.g., ChatOpenAI) inside Langraph nodes.
- Use environment (.env) for API keys; load with load_env().

---

## Simple bot (LLM integration)
- Goal: demonstrate calling an LLM inside Langraph nodes.
- Key imports:
  - from langchain.schema import HumanMessage
  - from langchain.chat_models import ChatOpenAI
  - StateGraph, TypedDict, load_env
- State schema:
  - class AgentState(TypedDict):
      messages: List[HumanMessage]
- LLM init:
  - lm = ChatOpenAI(model_name="gpt-4o" or "gpt-4o-mini")
  - load_env() to pull API keys
- Node implementation:
  - def process(state: AgentState) -> AgentState:
      response = lm.invoke({"messages": state["messages"]})  # conceptual
      # store response content as AIMessage or equivalent in state
      state["messages"].append(AIMessage(content=response.content))
      print(response.content)
      return state
- Graph: single node graph with start->process->finish; compile -> app.invoke.
- Simple conversation loop:
  - while True:
      user_input = input("Enter something: ")
      state["messages"].append(HumanMessage(content=user_input))
      app.invoke(state)
- Limitations:
  - No persistent memory: exiting program loses conversation state.
  - Token cost: conversation history grows indefinitely, increasing costs.

- Quick fix for persistence (prototyping):
  - Write conversation history to a text file: open("log.txt","w") and iterate messages; label as "You:" or "AI:" and write content.
  - Works for prototypes; production should use a DB/vector DB.

- Token management:
  - Simple strategy: prune history to last N messages (e.g., keep last 5–10 messages) before invoking model to constrain token usage and cost.

---

## Chatbot with memory (improved memory handling)
- Goal: maintain full conversation history in state and persist across runs.
- Use both HumanMessage and AIMessage in the messages list via Union:
  - class AgentState(TypedDict):
      messages: List[Union[HumanMessage, AIMessage]]
- Flow:
  1. On each user input:
     - append HumanMessage(content=user_input) to state["messages"]
     - invoke agent (compiled app) with the whole state["messages"]
     - node processes LLM response, appends AIMessage(content=response.content)
  2. Persist conversation after session:
     - write conversation log (iterating messages) to file for persistence.
- Benefits:
  - Agent can reference and remember previous messages during a live session.
  - Persistence to file or DB prevents forgetting across program restarts.
- Caveats & mitigations:
  - Conversation history grows — trim older messages to manage token usage/cost.
  - Persisting to text file is quick for prototypes; use a database/vector store in production.

# React agent (REAct: Reasoning + Acting) — overview and important building blocks
- Concept: Agent loops, reasons (via LLM), decides to call tools (act), receives tool results (tool messages), and continues until termination condition.
- Typical structure:
  - start -> agent (LLM reasoning) -> [tool nodes] -> agent -> ... -> finish
  - Agent uses tool outputs to form subsequent reasoning steps; loop continues until agent indicates completion.

Important imports and concepts explained:
- Annotated
  - Adds metadata to a type without changing the underlying type.
  - Use-case: provide validation/semantic hints (e.g., "must be valid email format") in schema.
- Sequence
  - Type annotation representing ordered collections; used to declare message sequences.
  - Useful when combined with a reducer to avoid manual list manipulations (Langraph convenience).
- BaseMessage, ToolMessage, SystemMessage
  - BaseMessage: foundational parent class that message types inherit from.
  - ToolMessage: content returned by tools, includes metadata (e.g., tool call id).
  - SystemMessage: instructions for the model (e.g., role/system-level guidance).
- add_messages (reducer function)
  - Reducer controls how node updates merge into existing state (avoids blind overwrites).
  - add_messages specifically appends incoming messages to an existing message sequence.
  - Without a reducer, updates would overwrite keys — reducer allows combining updates (append rather than replace).

Typical state pattern for a React agent
- Use an annotated Sequence[BaseMessage] with add_messages to automatically handle appending messages into the conversation history:
  - from typing import Annotated, Sequence
  - class AgentState(TypedDict):
      messages: Annotated[Sequence[BaseMessage], add_messages]
- Rationale:
  - The agent and tool nodes will produce messages (HumanMessage / AIMessage / ToolMessage).
  - The reducer ensures new messages are merged into messages sequence instead of replacing it.

(Next step: define the agent TypedDict state and implement tools, tool nodes, router/agent logic, system messages, and the main graph loop. The course continues with concrete code for the React agent based on the annotated Sequence[BaseMessage] state schema.)