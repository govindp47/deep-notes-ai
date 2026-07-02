# LangGraph Course

## Course Introduction

- Course on Langraph: Python library for conversational AI workflows.
- Learn to design, implement, and manage dialogue systems using graphs.
- Outcome: build scalable conversational applications leveraging large language models.

- Instructor: Vava, robotics and AI student.
- Assumes prior knowledge of Langraph but no coding experience.
- Detailed explanations provided; pacing may be slow.

- Course activities: building graphs and AI agents, learning theory.
- Exercises provided with answers on GitHub.

## Type Annotations

### Section Overview

- Focus: type annotations.
- Theoretical section; important for coding AI agents and graphs in Langraph.

### Dictionaries

- Topic: Dictionaries
  - Data structure with key-value pairs.
  - Example: `movie` dictionary with keys `name` ("Avengers Endgame") and `year` (2019).

- Properties of dictionaries:
  - Efficient data retrieval via unique keys.
  - Flexible but can lead to structure-related errors in large projects.
  - Solution: use TypedDict for type safety.

### TypedDict

- TypedDict:
  - Class implementation defining data types for keys.
  - Example: `name` as string, `year` as integer.
  - Used extensively in Langraph for state definitions.

- Benefits of TypedDict:
  - Type safety reduces runtime errors.
  - Enhanced readability aids debugging.

### Union

- Union type annotation:
  - Specifies that a value can be multiple defined types.
  - Example: function input `x` can be int or float; passing a string fails.

### Optional

- Optional type annotation:
  - Indicates a parameter can be a specific type or `None`.
  - Example: `nice_message(name)` can take a string or `None`.

### Any Type

- Any type annotation:
  - Allows any value.
  - Example: `print_value` function can accept any input.

### Lambda Functions

- Lambda functions:
  - Create small functions efficiently.
  - Example: square function using `map` to square numbers in a list.

### Summary

- Summary of type annotations:
  - Powerful tools in Langraph; high-level overview is sufficient.

## Langraph Core Elements

### State

- State in Langraph:
  - Shared data structure holding current application context.
  - Analogy: whiteboard in a meeting room for recording information.

### Node Concept

- Node concept in Langraph:
  - Functions/operations performing specific tasks.
  - Receives input (current state), processes it, and produces output.

### Graph Overview

- Graph in Langraph:
  - Structure mapping task connections and execution flow.
  - Analogy: roadmap showing routes and intersections.

### Edges and Conditional Edges

- Edges and conditional edges:
  - Edges connect nodes, determining execution flow.
  - Conditional edges decide next node based on current state conditions.

### Start and End Nodes

- Start and end nodes:
  - Start node: entry point for workflow.
  - End node: signifies workflow completion.

### Tools and Tool Nodes

- Tools and tool nodes:
  - Tools are specialized functions for tasks (e.g., fetching data).
  - Tool nodes run tools and connect outputs back to state.

- State graph:
  - Manages nodes, edges, and overall state for unified workflow.

### State Graph and Runnables

- Runnables in Langraph:
  - Standardized executable components for tasks.
  - Difference from nodes: runnables can represent various operations.

### Message Types

- Common message types in Langraph:
  - Human, AI, System, Tool, Function messages.

### Section Close

- Section conclusion.

## Getting Started Coding

- Starting coding in Langraph.
- Focus on building graphs, not AI agents yet.

- Goals for introductory coding:
  - Build basic graphs, understand syntax, and data flow.

## Hello World Graph

### Imports

- First graph setup:
  - Imports: `dict`, type dictionary, `state graph`.
  - Create agent state.

### Agent State Definition

- Agent state definition:
  - Shared data structure as typed dictionary.
  - Input: `message` (string).

### Greeting Node

- Greeting node:
  - Standard Python function taking state as input.
  - Updates state with greeting message.

### Build Graph

- Building the graph:
  - Use `state graph` to create and compile graph.
  - Add nodes with `graph.add_node` and set entry/exit points.

### Compile and Run

- Compile and run notes:
  - Compilation does not guarantee successful execution; logical errors may exist.

- Running the compiled graph:
  - Use `invoke` method; retrieve result from `message` attribute.

### Result Explanation

- Result explanation:
  - Access result via `message` attribute; demonstrates flow.

### Exercise: Compliment Agent

- Exercise: create a personalized compliment agent.
  - Task: output a compliment using concatenation.

## Graph 2 — Multiple Inputs

### Section Intro

- Introduction to Graph 2 — Multiple Inputs:
  - Build on previous graph, allowing multiple inputs.

### Imports and State Schema

- Imports and state schema for multiple-input graph:
  - Implement `AgentState` as typed dictionary with multiple keys.

### Processing Node

- Processing node for multiple-input graph:
  - Define `process_values` function to handle inputs and return updated state.

### Graph Assembly and Test

- **Graph Assembly Steps:**  
  1. Initialize graph with `AgentState` schema: `graph = StateGraph(AgentState)`.
  2. Add node: `graph.add_node(name="processor", action=process_values)`.
  3. Attach entry point to processor node.
  4. Attach finish point to processor node.
  5. Compile graph: `graph.compile()`.

- **Notes:**  
  - Similar structure to previous sections: node, start point, endpoint.
  - Visualize resulting graph for clarity.

- **Testing and Invocation Steps:**  
  1. Compile graph: `app = graph.compile()`.
     - Store compiled graph; invoking without compiling fails.
  2. Invoke graph: `answers = app.invoke(inputs)`.
  3. Example inputs:  
     - Integers: `[1, 2, 3, 4]`, Name: "Steve".
  4. Print `answers` to inspect output.

- **Expected Output:**  
  - `values`: `[1, 2, 3, 4]`, `name`: "Steve", `result`: "Hi there, Steve. Your sum is equal to 10."

### Debugging and Print Statements

- **Debugging with Print Statements:**  
  - Add print statements to show state before and after actions.
  - Inputs: `values` as `[1, 2, 3, 4]`, `name` as "Steve".
  - Access computed value directly with `result`.

- **Important Behavior:**  
  - If `result` not passed, defaults to `None`.
  - Using `state.result` when `None` can cause issues; ensure proper initialization.

### Exercise: Operation Node

- **Exercise Prompt:**  
  - Complete exercise to reinforce understanding.

### Exercise Details

- **Exercise Details:**  
  - Build graph with three inputs:  
    - List of integers, Name, Operation.
  - Node behavior:  
    - If operation is "plus", sum elements; if "times", multiply.
  - Example input:  
    - Name: "Jack Sparrow", Values: `[1, 2, 3, 4]`, Operation: "multiplication".
  - Expected output:  
    - "Hi Jack Sparrow, your answer is 24."  
  - **Implementation Note:**  
    - Use if statement to branch between operations.

### Exercise Closing

- **Exercise Closing Note:**  
  - Instructor will review after exercise completion.

### Extra Exercise Prompt

- **Extra Exercise Prompt:**  
  - Implement operation behavior in a single node:  
    - If "plus", add; if "times", multiply.
  - Example input:  
    - Name: "Jack Sparrow", Values: `[1, 2, 3, 4]`, Operation: "multiplication".
  - Expected output:  
    - "Hi Jack Sparrow, your answer is 24."  
  - **Implementation Note:**  
    - Use if statement for operation selection.

## Graph 3 — Sequential Graph

### Intro and Goals

- **Introduction to Sequential Graph:**  
  - Goal: Build a sequential graph with multiple nodes processing state.
  - Key points:  
    - Connect nodes through edges.
    - Invoke graph to observe state transformations.

### State Schema

- **Coding Setup for Sequential Graph:**  
  - Imports: `state_graph`, `typed_dict`.
  - Define state schema:  
    - `class AgentState`:  
      - Attributes: `name: str`, `age: str`, `final: str`.
  - Build node functions for actions.

### First Node

- **First Node (`first_node`) Design:**  
  - Function signature: pass in state, return updated state.
  - Behavior:  
    - Update `state.final`: `state.final = f"{state.name}, hi there."`.

### Second Node and Logical Error

- **Second Node (`second_node`) Design:**  
  - Behavior (initial version):  
    - `state.final = f"You are {state.age} years old."`
  - **Logical Error:**  
    - Overwrites previous greeting; fix by concatenation:  
      - `state.final = f"{state.final} {state.age} years old."`.

### Graph Construction

- **Graph Construction Steps:**  
  1. Create graph: `graph = StateGraph()`.
  2. Add nodes: `first_node`, `second_node`.
  3. Set entry and endpoint.
  4. Connect nodes with edge: `graph.add_edge(first_node, second_node)`.

### Invoke and Results

- **Invocation and Results:**  
  1. Invoke graph with parameters: `"Charlie"`, `"20"`.
  2. Print result:  
     - Output: `"Hi Charlie, you are 20 years old."`.
  - **Observations:**  
    - Demonstrates multiple nodes and state progression.

### Exercise: Three-node Sequence

- **Exercise for Three-node Sequence:**  
  - Requirements:  
    1. Build three nodes in sequence.
    2. Inputs: Name, Age, Skills.
    3. Node behaviors:  
       - Personalize greeting, describe age, list skills.
    4. Output combined result.

## Graph 4 — Conditional Graph

### Overview and Goals

- **Overview of Conditional Graph:**  
  - Goal: Build a conditional graph with multiple operations.
  - Create router node for decision-making.

### Imports and State

- **Imports and State Design for Conditional Graph:**  
  - Imports: `state_graph`, `typed_dict`, `start`, `endpoint`.
  - State schema:  
    - `class AgentState`:  
      - Attributes: two numbers, `operation` ("plus" or "minus"), `final` result.

### Adder, Subtractor, Router Nodes

- **Node Functions:**  
  - `adder`: Adds two numbers.
  - `subtractor`: Subtracts two numbers.
  - `decide_next_node`: Router function based on `state.operation`.

### Pass-through Lambda Explanation

- **Using Pass-through Lambda for Router:**  
  - Use `lambda state: state` for router when no state change occurs.
  - Distinction: Comparison vs. Assignment.

### Start-Connection and Router Role

- **Start Connection and Router Role:**  
  - Use `start` to connect to router node.
  - Router must be first node to decide routing.

### Conditional Edge and Path Map

- **Using `graph.add_conditional_edge`:**  
  - Parameters: Source (router), Path (decision function), Path map (edge to node mapping).

### Compile, Invoke, and Recap

- **Final Compilation and Invocation:**  
  - Connect nodes to endpoint, compile graph: `app = graph.compile()`.
  - Example invocation:  
    - Inputs: 10, "minus", 5; output: 5.

### Exercise: Extended Conditional

- **Exercise (Extended Conditional):**  
  - Build graph for four numbers and two operations.
  - Example: 10 - 5 = 5, 7 + 2 = 9.

## Graph 5 — Looping Graph

### Intro and Objectives

- **Introduction to Looping Graph:**  
  - Learn to implement looping and route data back to nodes.

### Graph Plan and State

- **Graph Plan and State for Looping Graph:**  
  - Plan: Start and end points, loop between nodes.
  - State schema: `name`, `numbers`, `counter`.

### Greeting and Random Nodes

- **Building Greeting and Random Nodes:**  
  - Greeting node: Outputs greeting with name.
  - Random node: Generates random numbers, tracks count.
  - Control logic: `should_continue` function for looping.

### Loop Control Function

- **Loop decision function:** Create `should_continue` function to decide routing. Returns loop edge and exit edge if counter < 5.
- **Loop trajectory:** 1. Start at `greeting` node. 2. Enter `random` node. 3. Exit `random` node 5 times. 4. After 5 iterations, exit.
- **Graph construction steps:** 1. Initialize graph. 2. Add nodes: `greeting`, `random`. 3. Create edge between `greeting` and `random`.

### Graph Construction and Conditional Edges

- **Graph construction:** Initialize graph, add nodes `greeting`, `random`, and create conditional edges with `random` as source and `should_continue` as routing function.
- **Routing behavior:** If loop output, route back to `random`; otherwise, route to endpoint.
- **Finalizing graph:** Set entry point, compile graph to match intended structure.

### Example Run and Notes

- **Example run details:** Set name, initialize list, counter = -1. Output shows greeting and random numbers. Counter = 5; if not set to 0, would generate 6 times.
- **Exercise status:** Final code for last graph; complete Graph 5 exercise.

### Exercise: Higher or Lower Game

- **Higher-or-Lower game requirements:** Automatic guessing game, bounds 1-20, max guesses 7. Stop if correct guess; loop until limit reached.
- **Automation:** Graph guesses automatically, hint node indicates "higher" or "lower."
- **Required input/state:** Player name, empty guesses list, `attempts` = 0.

## Environment and Basic LLM Agent

### .env File

- **Purpose of `.env` file:** Stores sensitive info (API keys, config values) for security.
- **API key necessity:** Required for external LLM calls; not needed for local LLM integrations.
- **Loading API key in Python:** `load_dotenv()`.

### Agent State for LLM

- **Agent state definition:** Create `AgentState` class as typed dictionary.
- **Required attributes:** Minimal; primary attribute is `messages`, a list of `HumanMessage`.

### Initialize LLM

- **Initializing LLM:** Instantiate with `lm = ChatOpenAI()`, using GPT-4. Other models: ChatAnthropic, ChatOpenAI.
- **Cost considerations:** Affordable; GPT-4 mini model available. Tokens priced in pennies.
- **Node behavior:** Define `process` function to return state. Call LLM with `lm.invoke()`, supply `state.messages`.

### Process Node and Invoke

- **`process` node workflow:** 1. Define `process` function to return `state`. 2. Invoke LLM with `lm.invoke()`, passing `state.messages`. 3. Store result in `response`. 4. Print response, return state.

### Run Example and Loop

- **User input and running agent:** Example: `user_input = input("Enter something:")`. Invoke agent with input.
- **Example runs:** `python agentbot.py` with inputs like "hi" yields AI responses. Confirm LLM functionality.
- **Limitations:** Simple bot lacks memory; cannot recall personal info.

## Chatbot with Memory

### Goals and Imports

- **Goals for next system:** Build AI with memory to remember interactions.
- **Objectives:** Use human and AI messages, maintain conversation history, utilize GPT-4 with LangChain.
- **Setup notes:** Similar imports, add AI message type and `Union` type annotation.

### State with Union and Messages

- **Message types in state:** Include AI messages for memory-capable chatbot.
- **Using `Union`:** Simplifies state structure by allowing both human and AI messages in one list.

### Model and Node Behavior

- **Libraries and approach:** Recommend using LangGraph for agentic systems.
- **Model setup:** Initialize LLM with GPT-4, create node with modified actions, add docstring for input request.

### Run Demo and Observe Memory

- **Post-processing:** Replace conversation history with result messages.
- **Running memory-enabled agent:** Execute `python memory_agent.py` to test memory.
- **Example interaction:** User states name; AI recalls it, demonstrating memory.

### Limitations and Solutions

- **Limitations of memory implementation:** 1. Persistence: Store conversation history in a text file or database. 2. Growing state size: Limit stored messages to manage costs.

### Section Summary

- **Section summary:** Learned to integrate human and AI messages for a memory-capable chatbot.
- **Next step:** Build a React agent.

## React Agent and Tools

### Introduction

- **Introduction to React agent:** Focus on reasoning and acting; common in AI development.
- **Objectives:** Build React graph, work with message types, test graph robustness.

### Typing: Annotated & Sequence

- **Typing imports:** Import `Annotated`, `Sequence`, `TypedDict` from `typing` module.
- **`Annotated`:** Adds metadata without changing data type.
- **`Sequence`:** Simplifies state updates for sequences.

### Env and Message Types

- **Environment and message-type imports:** Import `env` for API keys, new message types: `base message`, `tool message`, `system message`.
- **`tool message`:** Used for data passed back to LLM after tool call.
- **`system message`:** Provides instructions to LLM.

### Reducer Functions

- **Additional imports:** `tool`, `tool nodes`, and `add_messages` reducer function.
- **Reducer functions:** Define how updates merge with existing state; prevents overwriting.
- **Purpose of `add_messages`:** Aggregates data by appending messages.

### State and Tool Creation

- **Creating React agent state:** State has key `messages`, uses `sequence` type annotation and `add_messages` reducer.
- **Creating a tool:** Define function with decorator; example: `def add(a: int, b: int)`.

### Model Binding and Agent Node

- **Tools**: Currently one tool; future support for multiple tools planned.
- **Model Creation**: `model = chat.openAI` (uses `GPT-4`).
- **Binding Tools**: Use `bind_tools` to connect tools to the LLM.
- **Agent Node**: Define with `def model_call(state: agent_state)`; returns agent state.
- **System Message**: Example: `"You are my AI system. Please answer my query to the best of your ability."`
- **State Updates**: Use `messages_response` to update messages; `add_messages` reducer appends messages.
- **Invocation Detail**: Must pass query: `state['messages'] = human_message` to store human input.

### Conditional Edge and Looping Tools

- **Conditional Edge Purpose**: Determines if the graph continues or ends based on tool calls.
- **Conditional Edge Function**: `def should_continue(state)` returns `continue` when appropriate.
- **Loop Behavior**: If more tool calls are needed, follow the `continue` edge; otherwise, end the graph.
- **Graph Structure**: Initialize with `state_graph`, create agent node `R_agent`, and tool node; set entry point to `R_agent`.

### Graph Assembly and Compile

- **Graph Assembly**: Initialize with `state_graph`, add agent node `R_agent`, and tool node (e.g., `add`).
- **Entry Point**: Set to `R_agent`.
- **Conditional Edge**: Connects agent to tool node or endpoint; creates a loop.

### Helper and Examples

- **Helper Function**: Improves tool calling and output formatting.
- **Example Usage**: Input `"add 3 + 4."` streams data and returns `7`.
- **Docstring Requirement**: Must include a docstring; absence causes errors.
- **Loop Demonstration**: Executes multiple commands to show tool calling behavior.

### Extend Tools and Complex Commands

- **Extending Tools**: Add tools like `subtract` and `multiply`.
- **Complex Command Example**: `"add 40 + 12 and then multiply the result by 6."` returns `312`.
- **Non-tool Commands**: Handles queries like `"tell me a joke."` gracefully.

### React Agent Summary

- **Key Takeaways**: Understand how to create a react agent and use external tools and graphs.

## Drafter Project

### Project Overview

- **Project Overview**: Build a fourth AI agent for drafting documents.
- **Requirements**: Support human-AI collaboration, fast operation, and draft saving.

### Global Variable Strategy

- **Drafter Design Difference**: Tools do not always return to the AI agent in the same way.
- **Global Variable Strategy**: Use global variables to pass state into tools.

### Agent State and Tools

- **Agent State Definition**: `class agent_state(messages: annotated[sequence[base_message]], add_messages: reducer_function)`.
- **Tools Overview**: Includes `update` and `save` tools.
- **Update Tool**: `def update(content)` updates document content.
- **Save Tool**: Requests a file name and saves content; must end with `.txt`.

### Model, System Prompt, and Robustness

- **Model and Tool Binding**: Bind tools for LLM usage.
- **Agent Initialization**: `def r_agent(state: agent_state)`.
- **System Prompt**: Example: `"You are Drafter, a helpful writing assistant."`
- **Robustness Measures**: Handle empty state and provide user prompts.

### Conditional Edge: Continue vs End

- **Conditional Edge Behavior**: Checks last tool message to decide whether to continue or end.
- **Tool Usage**: `save` tool ends the program; `update` tool continues the loop.

### Formatting, Graph Build, Run

- **Print Formatting Helper**: Formats print statements for readability.
- **Graph Build**: Initialize `state_graph`, add nodes, and compile the graph.

### Extensions and Notes

- **Possible Extensions**: Add voice features, implement a GUI, integrate a knowledge base.

## RAG Agent (Retrieval-Augmented Generation)

### RAG Overview

- **RAG Overview**: Build a fifth AI agent focused on retrieval-augmented generation (RAG).
- **Temperature Parameter**: Controls model stochasticity; `0` for deterministic, `1` for stochastic.

### Embeddings and Document Loading

- **Document Specification**: Specify PDF for stock market data.
- **Loader Behavior**: Error handling for missing documents.
- **Chunking Configuration**: `chunk_size = 1,000` tokens, `chunk_overlap = 200` tokens.

### Chunking and Vector DB

- **Chunking Recap**: Divides documents into chunks with overlap for context.
- **Retriever Tool**: Returns relevant chunks for a query; handles no relevant information case.

### Retriever Tool

- **Retriever Binding**: Bind retriever tool to LLM; create agent state.
- **System Prompt**: Detailed instructions to minimize hallucinations.

### Graph Assembly and Test

- **Graph Assembly**: Bind tools, create agent state, and compile graph.
- **Query Loop Function**: Allows user queries; exit with `"exit"` or `"quit."

### Run Demo and Results

- **Running RAG Demo**: Execute with `python rag_agent.py`.
- **Example Queries**: Retrieves information from the document; handles irrelevant queries.

## Conclusion

- **Closing**: Contact on LinkedIn for questions; thanks for watching.
