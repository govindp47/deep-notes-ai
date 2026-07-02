# LangGraph Course

## Course Introduction

- Welcome to this video course on Langraph, the powerful Python library for building advanced conversational AI workflows.
- In this course, Vbeca will teach you how to design, implement, and manage complex dialogue systems using a graph-based approach.
- By the end, you'll be equipped to build robust, scalable conversational applications that leverage the full potential of large language models.

- Instructor:
  - My name is Vava, and I'm a robotics and AI student.
- Course assumptions and pacing:
  - I assume you've heard of Langraph before, hence why you clicked on this course.
  - I also assume you have never coded in Langraph before.
  - Because of this assumption, I have explained every single thing in as much detail as I possibly can.
  - This might mean that I will be going slow at times; you can always speed me up if you want.

- What we'll do in the course:
  - We will be building a lot of graphs and AI agents.
  - We will learn a lot about the theory.
  - Exercises are provided throughout the course, with all answers available on GitHub.
- Transition:
  - If you're ready to start this journey with me, let's go to our first section.

## Type Annotations

### Section Overview

- Focus of this section:
  - We will cover type annotations.
  - This will be a completely theoretical section, but it will be short and brief.
- Rationale:
  - When we eventually code our AI agents and graphs in Langraph, type annotations will start appearing everywhere.
  - I don't want you to start coding without having seen these before or without knowing what they actually are.

### Dictionaries

- Topic: dictionaries
  - Dictionaries are a data structure.
  - Example described: a simple dictionary called movie with two keys and values:
    - keys: `name`, `year`
    - values: "Avengers Endgame" and 2019.

- Properties and limitations of dictionaries:
  - Dictionaries allow for efficient data retrieval based on their unique keys.
  - They are flexible and easy to implement.
  - Potential problem: ensuring that the data follows a particular structure can be challenging, which can be a huge problem in larger projects.
  - In simple terms, dictionaries do not check if the data is the correct type or structure, which can lead to logical errors in your project.
  - In large projects, identifying such errors could be quite a headache.
- Solution introduced:
  - The solution for this is something called a type dictionary.

### TypedDict

- Type dictionary (TypedDict) as the solution:
  - Implemented as a class.
  - Example context: the same movie example from earlier is implemented with a typed dictionary class.
  - In that class, the actual data type of each key is defined (for example, `name` is a string and `year` is an integer).
  - Initialization example described: the same values "Avengers Endgame" and 2019 are used to initialize the typed dictionary.
  - Note: this type annotation is used extensively in Langraph to define states.
  - A type dictionary is easy to implement; you implement it as a class.

- Two main benefits of using a type dictionary:
  - Type safety: we've explicitly defined what should be in this data structure, which reduces runtime errors.
  - Enhanced readability: making debugging easier if something goes wrong within this type dictionary.

### Union

- Union type annotation:
  - Union specifies that a value can be either of the defined data types.
  - Example described: a simple function that takes in a value and squares it.
    - The input `x` could be either an integer or a float; union indicates that `x` can only be an integer or a float.
    - If 5 or 1.234 is passed in, this is fine; passing in a string would fail.
  - Usefulness: in more complicated applications, union is useful for type safety, helping to catch incorrect usage.

### Optional

- Optional type annotation:
  - Optional indicates that a parameter could either be a specific type or `None`.
  - Example described: a function called `nice_message` that takes in a `name`.
    - If you pass in a name, it will say "Hi there, [name]."
    - If you don't pass in anything, optional indicates that the `name` parameter could either be a string or `None`.
    - If nothing is passed, it will say "Hey, random person."
    - It cannot be anything else; it must be either a string or `None`.

### Any Type

- `Any` type annotation:
  - `any` means the value could be anything.
  - Example described: a simple function called `print_value` that takes in something and prints it.
    - For example, if a string is passed in, it prints it; anything is allowed.

### Lambda Functions

- Lambda functions (as a discussed topic, presented as a type of concise function):
  - Lambda functions are useful for creating small functions efficiently.
  - Example described: a square function that takes in a number and squares it; passing in 10 gives 100.
  - Another example described: using a lambda with the `map` function to square each number in a list.
  - Summary: lambda functions are shortcuts for writing small functions, making things efficient.

### Summary

- Summary of type annotations section:
  - You can see how powerful these type annotations are; they will come up frequently.
  - You don't need to memorize this; just have a high-level overview of what they are.

## Langraph Core Elements

### State

- The concept of state in Langraph:
  - A state is a shared data structure that holds the current information or context of the entire application.
  - In simpler terms, it is like the application's memory, keeping track of the variables and data that nodes can access and modify as they execute.
  - Analogy: think of the whiteboard in a meeting room — each time you want to record or update information, you write it on the whiteboard, which acts as your state while the participants act as nodes.
  - The state shows the updated content of your entire application.

### Node Concept

- The concept of a node in Langraph:
  - Nodes are individual functions or operations that perform specific tasks within the graph.
  - Each node receives an input, often the current state of your application, processes it, and produces an output or an updated state.
  - Analogy: an assembly line station, where each station performs a specific job; each station represents a node because it does one specific task.
  - To connect these different nodes together, we need to understand the graph.

### Graph Overview

- The graph in Langraph:
  - The graph is the overarching structure that maps out how different tasks, or nodes, are connected and executed.
  - It visually represents the workflow, showing the sequence and conditional parts between various operations.
  - Analogy: think of it as a roadmap, displaying different routes connecting cities with intersections offering choices on which path to take next.

### Edges and Conditional Edges

- Edges and conditional edges:
  - Edges are the connections between nodes that determine the flow of execution; they tell the application which node should be executed next after the current one completes its task.
  - Analogy for an edge: a train track connecting two stations, where the train represents the state being updated from one station to another.
  - Conditional edges decide the next node to be executed based on specific conditions applied to the current state.
  - Analogy for a conditional edge: a traffic light, where the light color decides the next step.

### Start and End Nodes

- Start and end nodes:
  - The start point, or start node, is a virtual entry point in Langraph that marks where the workflow begins; it doesn't perform any operations itself but serves as the designated starting position for the graph's execution.
    - Analogy: the starting line of a race.
  - The end node signifies the conclusion of the workflow in Langraph; when the application reaches this node, the graph's execution stops, indicating that all intended processes have been completed.
    - Analogy: the finish line in a race.

### Tools and Tool Nodes

- Tools and tool nodes:
  - Tools are specialized functions or utilities that nodes can utilize to perform specific tasks, such as fetching data from an API.
  - Tools enhance the capabilities of nodes by providing additional functionalities.
  - The difference between a tool and a node: a node is part of the graph structure, while tools are functionalities used within the nodes.
  - Analogy: tools in a toolbox, where each tool has a distinct purpose.
  - A tool node is a special kind of node whose main job is to run a tool.
    - Example described: a tool node could be a node that uses a tool to fetch data from an API and connects the tool's output back into the state for other nodes to use.

- The state graph:
  - The state graph is an important element that builds and compiles the graph structure.
  - It manages the nodes, edges, and overall state, ensuring that the workflow operates in a unified way and that data flows correctly between components.

### State Graph and Runnables

- The state graph (continued) and runnables:
  - Analogy for the state graph: a blueprint of a building, outlining the design and connections within the building.
  - Runnable in Langraph:
    - A standardized executable component that performs a specific task within an AI workflow.
    - Acts as a fundamental building block, allowing creation of modular systems.
  - Difference between a runnable and a node:
    - A runnable can represent various operations, while a node typically receives a state, performs an action, and updates the state.
    - Analogy for a runnable: a Lego brick, which can be combined to create sophisticated AI workflows.

### Message Types

- Common message types in Langraph (five most common):
  - Human message: represents input from a user.
  - AI message: represents responses generated by AI models.
  - System message: provides instructions or context to the model.
  - Tool message: specific to tool usage.
  - Function message: represents a function call.
- Note: if you've used an API like a large language model API before, many of these will be familiar, especially the system message, AI message, and human message.

### Section Close

- This concludes this section.

## Getting Started Coding

- We're about to start coding in Langraph for the very first time.
- Now that the theory is covered, we will code up some graphs.
- We will code our very first graph in the upcoming subsection.
- Confession and rationale:
  - We are not going to be building any AI agents in this section.
  - This is because we haven't seen how to code in Langraph yet, and combining LLMs, APIs, and tools could be messy and confusing, especially since we have never coded in Langraph before.
- Course design note:
  - This course is designed to be beginner-friendly, detailed, and comprehensive; we will proceed step by step.
  - Don't worry; we will be coding AI agents soon.

- Goals for the introductory coding section:
  - Build a couple of graphs to understand Langraph better, including the syntax and how to code graphs confidently.
  - The first graph is called the hello world graph — the most basic form of a graph we can code in Langraph.
- Objectives when building the hello world graph:
  - Understand and define the agent state structure.
  - Create simple node functions, process them, and update the state.
  - Build the first basic Langraph structure and understand how to compile, invoke, and process it.
  - The main goal is to understand how data flows through a single node in Langraph.
  - The graph will have a start point and an end point, with nodes sandwiched in between.

## Hello World Graph

### Imports

- Beginning the first graph (imports and next steps):
  - Imported items described: `dict`, type dictionary, and `state graph`.
  - Clarification: `dict` and type dict are dictionary and type dictionary, while `state graph` is a framework that helps you design and manage the flow of tasks in your application.
  - The first thing after importing is to create the state of our agent, which we will call agent state.

### Agent State Definition

- Agent state definition and node input/output types:
  - The state is a shared data structure that keeps track of all the information as the application runs.
  - We will build the agent state through a class.
  - Create a class called agent state; the state needs to be in the form of a typed dictionary.
  - Pass in one input called `message`, specifying the data type as string.
  - Next, code the first node by defining a standard Python function.
  - The input type of a node needs to be the state, and the output type also has to be the state.
  - The state of our application is the agent state we defined earlier.

### Greeting Node

- Greeting node (implementation details described verbally):
  - Define the node as a standard Python function (a greeting node function) that takes in the state and specifies the output type as the state.
  - The function will return the updated state after performing actions.
  - Docstrings are important because they inform AI agents about what the function does.
    - Write a docstring stating that this is a simple node that adds a greeting message to the state.
  - Update the state by manipulating the `message` part of the state (for example, concatenate "Hey" with the state message).
  - Finally, return the updated state.

### Build Graph

- Building the graph (using the state graph framework):
  - To create a graph in Langraph, use the state graph attribute and pass in the state schema, which is the agent state.
  - Store the resulting graph in a variable called `graph`.
  - To add a node to this graph, use `graph.add_node`, which requires two parameters: the name of the node and the action it will perform.
    - Example: name the node "greeter" and specify the action as the greeting node function.
  - Add the start and end points to the graph by calling the inbuilt function `set_entry_point` and passing the key of the node you want the start node to connect to.
    - In the example, pass "greeter" as the key for both the start and end points.
  - Finally, compile the graph using the inbuilt `compile` function and store it in a variable.
  - Caution: just because the graph compiles without errors doesn't mean it will run successfully; there could be logical errors in more complicated graphs.

### Compile and Run

- Compile and run notes:
  - Compile the graph and store the compiled object in a variable.
  - Compilation without errors does not guarantee the graph will run successfully; logical errors may still exist.
  - The instructor notes: "There might be logical errors. Trust me, I know."
  - Visualization suggestion: you can use the IPython library to help visualize this.
  - The code described is very similar to the first graph the instructor showed earlier; the only difference in the later example is the name of the node, which was set to "greater."
  - The name "greater" was used because that's the name given to that node in the example.

- Running the compiled graph:
  - To run it, use the built-in method `invoke`.
  - Example invocation described: pass in the message as something like "Bob" and store the result in a variable.
  - To get the value of the result, reference the attribute `message`.
    - The only attribute in the entire graph is `message`, so retrieving `message` yields the final answer.
  - Example final answer described: "Hey Bob, how's your day going?"
    - This result is produced by concatenating "Hey," the input message (the name), and "how's your day going?"
  - The instructor notes these message templates could be changed to anything else; the functions are almost endless.

### Result Explanation

- Result explanation (reiterated):
  - To obtain the value of `result`, reference the attribute `message`.
  - The only attribute in the graph is `message`.
  - The returned message in the example is "Hey Bob, how's your day going?"
    - It is formed by "Hey," concatenation of the input name, and "how's your day going?"
  - This demonstrates the flow of how everything works.

### Exercise: Compliment Agent

- Exercise: create a personalized compliment agent
  - Goal: solidify understanding of the Hello World graph.
  - Task description:
    - Create a personalized compliment agent.
    - Pass in your name, like "Bob", and then output something like: "Bob, you're doing an amazing job learning Langraph."
  - Hint: you need to concatenate the state, not replace it.
  - Note: this exercise is similar to what was just done and is intended to get your hands dirty.

## Graph 2 — Multiple Inputs

### Section Intro

- Introduction to Graph 2 — Multiple Inputs:
  - After completing the exercise, the next graph builds on the first.
  - This graph is similar to the first but will allow multiple inputs.
- Objectives for this graph:
  - Build a more complicated agent state.
  - Create a processing node that performs operations on list data.
  - Work with different data types apart from just strings.
  - Set up the entire graph that processes, outputs results, and computes them.
  - Main goal: learn how to handle multiple inputs.

### Imports and State Schema

- Imports and state schema for the multiple-input graph:
  - Imported items described: the type dictionary and the state graph (same as before), and additionally `list` this time.
  - Reminder: a list is a simple data structure.
  - State schema implementation notes:
    - Implement the state schema first using a class `AgentState` as a typed dictionary.
    - The name of the state schema could be arbitrary, but `AgentState` was chosen because it describes the state of your agent.
  - Main goal: handle and process multiple different inputs by creating multiple keys in the state.
    - Example keys described:
      - `values: List[int]` for a list of integers
      - `name` as a string
      - `result` as a string
  - Now the graph operates on two different types of data structures: a list of integers and a string.

### Processing Node

- Processing node for the multiple-input graph (implementation described verbally):
  - Inputs handled: `values`, `name`, and `result`.
  - Keep the graph simple by using a single node.
  - Define the node as `def process_values` that takes in the state and returns the updated state.
    - The function signature described: `state: AgentState` in, and `AgentState` out.
  - Include a docstring: "This function processes multiple different values and inputs."
  - Processing steps described:
    - Sum the values passed in (using `sum(state.values)`).
    - Concatenate the `name` into a greeting and store the combined text in `state.result`.
  - Finally, return the updated state.

### Graph Assembly and Test

- Steps to assemble the graph:
  1. Initialize a graph using the state graph and pass in the state schema `AgentState`; store this in the variable `graph`.
  2. Add a node using `graph.add_node`, which requires two parameters: the name and the action.
     - For this example, use the name "processor" and the action function `process_values`.
  3. Attach the entry point to the processor node (the node you just added).
  4. Attach the finish point to the processor node in the same manner.
  5. Compile the graph using `graph.compile`.

- Notes and reminders:
  - This construction is very similar to the previous section: a node, a start point, and an endpoint.
  - Visualize the resulting graph after these steps to understand how it will look.

- Testing and invocation:
  1. Compile the graph and store the compiled graph in a variable (for example, `app`).
     - Make sure you store the compiled graph; invoking the graph without compiling it won't work.
     - If you try `graph.get_graph` before compiling, it will fail because the graph hasn't been compiled yet.
  2. Invoke the compiled graph using the `invoke` function (invoke via `app`).
  3. Store the invocation result in a variable, for example `answers`.
  4. Example invocation inputs to pass in:
     - a list of integers: `[1, 2, 3, 4]`
     - the name: "Steve"
  5. Print `answers` to inspect the output.

- Expected output (as observed):
  - `values` are `[1, 2, 3, 4]`
  - `name` is "Steve"
  - `result` is the string "Hi there, Steve. Your sum is equal to 10."

### Debugging and Print Statements

- Debugging with print statements:
  - Add print statements to show the state before the action and after the action; this demonstrates how the state gets updated.
  - You will see the inputs such as `values` as `[1, 2, 3, 4]` and `name` as "Steve."  
  - If you only want to access the computed value, you can specify `result` to get it directly and more cleanly.

- Important behavior about `result` and state initialization:
  - If you don't pass `result` as an input, Langraph automatically sets it to `None`.
  - If you attempt to use `state.result` to update itself or rely on it when it is `None`, you can run into problems because `state.result` has been initialized as `None`.
  - Be mindful of that initialization behavior.
  - In the specific example discussed, assigning `state.result` worked because the code only assigns `state.result` (rather than depending on a prior non-None value).
  - After the action runs, you can observe that the `result` has been updated.

### Exercise: Operation Node

- Exercise prompt:
  - Complete the exercise to solidify your understanding of the material covered.
  - The instructor will see you at the exercise.

### Exercise Details

- Exercise details (second exercise):
  - Build a graph that passes in three inputs to a single node:
    - a list of integers
    - a name
    - an operation
  - Behavior required in the single node:
    - If the operation is "plus," add the elements of the list.
    - If the operation is "times," multiply all the elements of the list.
  - Example input:
    - name: "Jack Sparrow"
    - values: `[1, 2, 3, 4]`
    - operation: "multiplication"
  - Expected output format:
    - `"Hi Jack Sparrow, your answer is 24."`
  - Implementation note:
    - You will need an if statement inside the node to branch between addition and multiplication; this makes the node slightly more complicated, but the overall concept is the same.

### Exercise Closing

- Closing note for the exercise:
  - Once you've completed this exercise, the instructor will see you when building the third graph.

### Extra Exercise Prompt

- Exercise details (operation behavior and example):
  - If the operation is "plus," add the elements; if it's "times," multiply all the elements — all within the same node.
  - Example input:
    - name: "Jack Sparrow"
    - values: `[1, 2, 3, 4]`
    - operation: "multiplication"
  - Expected output format:
    - `"Hi Jack Sparrow, your answer is 24."`
  - Implementation note:
    - You would need an if statement in your node to choose between addition and multiplication; this makes the node slightly more complicated, but the whole concept is the same.

## Graph 3 — Sequential Graph

### Intro and Goals

- Introduction to the third graph (sequential graph):
  - Goal: build a sequential graph that creates and handles multiple nodes which sequentially process and update different parts of the state.
  - Key learning points:
    - How to connect nodes together in a graph through edges.
    - How to invoke the graph and observe how the state transforms step by step as the graph progresses.
  - Main objective: understand how to create and handle multiple nodes in Langraph.

### State Schema

- Coding setup for the sequential graph:
  - Imports: the same as before — state graph and typed dictionary.
  - As with the previous graphs, define the state schema (agent state) first.

- State schema (design notes):
  - Create `class AgentState` as a typed dictionary.
  - Include three attributes:
    - `name: str`
    - `age: str`
    - `final: str`

- Next step:
  - Build two node functions that will serve as the node actions.

### First Node

- First node (`first_node`) design and behavior:
  - Name the function `first_node`.
  - Function signature: pass in the state and return the updated state.
  - Docstring: indicate this is the first node of the sequence.
  - Behavior inside the node:
    - Manipulate the `final` attribute of the state.
    - Example assignment: `state.final = f"{state.name}, hi there."`
  - Return the state.

### Second Node and Logical Error

- Second node (`second_node`) design and behavior:
  - Name the function `second_node`.
  - Docstring: indicate this is the second node.
  - Behavior inside the node (initial, problematic version):
    - `state.final = f"You are {state.age} years old."`
  - Logical error identified:
    - The second node overwrites the greeting stored in `state.final` by replacing it with the age message.
    - The intention is to keep both messages (the greeting and the age description).
  - Fix by concatenation:
    - Use `state.final = f"{state.final} {state.age} years old."` to preserve the previous content and append the age message.
  - After concatenation, the logical error is resolved.

### Graph Construction

- Graph construction steps for the sequential graph:
  1. Create the graph framework using `state_graph`.
  2. Add the node functions to the graph:
     - add `first_node`
     - add `second_node`
  3. Set the entry point and the endpoint for the graph.
  4. Connect the first node to the second node using an edge.
     - Use `graph.add_edge` to create a directed edge from the first node to the second node.
  5. The flow of data/state updates moves from the first node to the second node.

### Invoke and Results

- Invocation and observed results:
  1. Invoke the compiled graph, passing the parameters `"Charlie"` and `"20"`.
  2. Print the result.
     - Observed output: `"Hi Charlie, you are 20 years old."`

- Additional observations and lessons:
  - This could have been performed in a single node, but the purpose was to demonstrate multiple nodes and how state progresses through them.
  - You learned how to use the `add_edge` method.
  - You can change the keys of your state at any point in the sequence.
  - Be mindful when replacing content in an attribute — doing so can introduce logical errors if you intended to preserve previous content.

### Exercise: Three-node Sequence

- Exercise for the three-node sequence (build on the example):
  - Requirements:
    1. Build three nodes in sequence instead of two.
    2. Accept the user's name, their age, and a list of their skills as inputs to the graph.
    3. Node behaviors:
       - First node: personalize the `name` field with a greeting.
       - Second node: describe the user's age.
       - Third node: list the user's skills in a formatted string.
    4. Combine these pieces and store the result in a `result` field, then output it.
  - Expected output format (example):
    - `"Linda, welcome to the system. You are 31 years old, and you have skills in Python, machine learning, and Langraph."`
  - Implementation notes:
    - You will need to use `add_edge` twice to chain the three nodes.
    - This exercise is intended to solidify your understanding of building graphs.
    - Answers for the exercises will be available on GitHub after completion.

## Graph 4 — Conditional Graph

### Overview and Goals

- Overview and goals for graph 4 (conditional graph):
  - Goal: learn how to build a conditional graph and implement conditional logic.
  - Use multiple nodes to perform different operations (for example, addition and subtraction).
  - Create a router node that handles decisions and controls graph flow.
  - Main objective: show how to create conditional edges in Langraph and wire routing logic into the graph.

### Imports and State

- Imports and state design for conditional graph:
  - Imports are slightly modified from previous graphs:
    - Include the type dictionary and `state_graph` as before.
    - Additionally import `start` and `endpoint`.
  - State schema design:
    - Define `class AgentState`.
    - Inputs: two numbers and an `operation` attribute, either `"plus"` or `"minus"`.
    - The `final` number will be the result of either adding or subtracting the two numbers.

### Adder, Subtractor, Router Nodes

- Node functions to create:
  - `adder`: a node function that adds the two numbers.
  - `subtractor`: a node function that subtracts the two numbers.
  - `decide_next_node`: a router node function that selects the next phase of the graph.
    - Behavior of the router: route the flow based on `state.operation`.
      - If `state.operation` is `"plus"`, return the edge for addition.
      - If `state.operation` is `"minus"`, return the edge for subtraction.

- Graph assembly and intended behavior:
  - Build the graph using `state_graph`, add nodes, and set entry/exit points.
  - Connect nodes with edges to route flow based on the operation.
  - After invoking, the graph should follow the branch selected by the router.

- Subtle issue to be aware of:
  - There is a subtle reason the graph as initially written will not work.
  - In `adder` and `subtractor`, the functions return the updated state.
  - In the router node (`decide_next_node`), the function returns an edge name but does not return the (updated) state.
  - The difference—returning state versus returning an edge—is significant in how Langraph expects node functions to behave; this mismatch prevents the graph from functioning as intended until addressed.

### Pass-through Lambda Explanation

- Using a pass-through lambda for the router when the router does not change state:
  - A solution is to use a pass-through function such as `lambda state` that returns the same state unchanged.
    - This makes the router's node return the state (matching the other nodes) while still routing based on the operation.
  - Rationale:
    - The router is comparing values (for example, checking whether `state.operation` is minus) but is not assigning or changing the state.
    - Because there is no assignment to state, the state remains exactly the same; therefore, it is safe to use a pass-through function.
  - Distinction emphasized:
    - Comparison (checking values) is different from assignment (changing values). The router does comparisons and routes accordingly, but does not modify the state itself.

### Start-Connection and Router Role

- Start connection and role of the router:
  - Initialization differences:
    - Instead of using "set entry point" and "set finish point" as before, import and use the `start` and `end` keywords (ensure you imported them).
    - `start` is a start point that you connect to the router node.
  - Why connect `start` to the router rather than directly to add/subtract nodes:
    - If the start point connected directly to add or subtract nodes, the router would be bypassed and would have no role.
    - The router must be the first node connected from the start so it can decide which node to route to based on the inputs.

- Introducing `graph.add_conditional_edge`:
  - This method sets up the conditional routing feature.
  - Parameters and structure:
    1. The source: the name of the node that will perform the routing (the router node).
    2. The path: the function that decides the appropriate path (e.g., the `decide_next_node` function).
    3. The path map: a dictionary mapping edge names to destination nodes (edge -> node).
  - Implementation notes:
    - The path map will specify which edge corresponds to the addition operation and which to the subtraction operation.
    - Addition and subtraction operations will be edge names that indicate the direction to the corresponding add or subtract node.

- Final connections and compilation:
  - Create two edges from the add node and subtract node to the endpoint:
    - Example: `graph.edge(start=add_node, end=endpoint)` and `graph.edge(start=subtract_node, end=endpoint)`.
  - Compile the graph with `app = graph.compile`.

- Visualization summary:
  - The resulting graph layout should look like: start → router → {add node, subtract node} → end.
  - Edge names correspond to operations (e.g., the addition operation edge leads to the add node; the subtraction operation edge leads to the subtract node).

### Conditional Edge and Path Map

- Using `graph.add_conditional_edge` and the path map:
  - Purpose: implement conditional routing from a source node (the router).
  - Parameters:
    1. Source: the name of the router node.
    2. Path: the function that decides which edge to follow (e.g., `decide_next_node`).
    3. Path map: a dictionary mapping edge names to destination nodes.
  - How it maps to the add/subtract nodes:
    - The path map describes which edge (operation name) leads to which node (add node or subtract node).
  - After setting up the conditional edges, create the endpoint connections:
    - Add an edge from the add node to the endpoint and an edge from the subtract node to the endpoint, for example:
      - `graph.edge(start=add_node, end=endpoint)`
      - `graph.edge(start=subtract_node, end=endpoint)`
  - Finally, compile the graph with `app = graph.compile`.

### Compile, Invoke, and Recap

- Final compilation, invocation example, and recap:
  - Endpoint connections and compilation:
    - Connect the add node and the subtract node to the endpoint with edges (one from each node).
    - Compile the graph: `app = graph.compile`.
  - Visualization:
    - The graph should look like: start → router → {add node, subtract node} → end, with edge names indicating the operation.
  - Invocation example and expected result:
    - Define inputs: number one = 10, operation = minus, number two = 5.
    - Because operation is subtraction, the final number should be 10 - 5 = 5.
    - Printed output shows: number one is 10, operation is minus, number two is 5, final number is 5.
  - Notes on invocation and method:
    - The invocation method shown may differ slightly from prior examples; this demonstrates another valid invocation approach.
  - Recap of steps taken:
    1. Import required items.
    2. Create the state schema (`AgentState`) as a typed dictionary.
    3. Create three nodes: add node, subtract node, and decide next node (router).
       - In the router, if the operation is plus, route to the addition operation edge; if minus, route to the subtraction operation edge.
    4. Add nodes to the graph.
    5. Add the edge from the start point to the router.
    6. Add the conditional edge from the router using the path function and path map (edge -> node mapping).
    7. Add edges from the add/subtract nodes to the endpoint and compile.
  - Encouragement and next step:
    - This may be confusing initially, but the exercise will help you understand the pattern by replicating it.

### Exercise: Extended Conditional

- Exercise (extended conditional):
  - Build a graph that processes four numbers and two operations, and outputs the final results for each operation.
  - Example scenario:
    - Inputs: number one, number two, number three, number four and two operations.
    - Example calculations: 10 - 5 = 5 and 7 + 2 = 9; both resulting numbers should be output.
  - Purpose:
    - This exercise solidifies understanding of conditional edges, which are important for future graphs and AI agents.
  - After completion, compare solutions on GitHub.

## Graph 5 — Looping Graph

### Intro and Objectives

- Introduction to graph 5 (looping graph) and objectives:
  - Context: this is the final graph in the section; knowledge from previous graphs helps when building AI agents.
  - Primary concept to learn: looping — route flow of data back to nodes.
  - Objectives for this graph:
    - Implement logic to loop and route data back into nodes.
    - Create a single conditional edge (knowledge carried over from the previous section).
  - Exercise guidance:
    - Complete the previous section's exercise (it may be the hardest so far); check GitHub if you need help.
    - There are multiple ways to build graphs in Langraph; ensure the graph is well built and functions correctly.
    - Optionally extend the graph for robustness.
  - Planning advice:
    - When building AI agent systems, plan the nodes and edges, whether conditional edges are needed, and where start and end points will be.
    - Use a blueprint (pen-and-paper or software) to design the graph before implementing.

### Graph Plan and State

- Graph plan and state for the looping graph:
  - High-level plan:
    - There will be a start and end point, and a loop between nodes.
    - Two primary nodes: a greeting node and a random node.
      - Greeting node: accept the user's name and output a greeting like "Hi there, {name}."
      - Random node: generate five random numbers and record them.
    - The loop will allow the random node to be revisited multiple times (five iterations in the example).
  - Design notes and caveats:
    - This example is intentionally simple for learning fundamentals; in practice the loop could be implemented differently (e.g., with a for-loop), but it is shown here to teach graph looping.
  - State schema (AgentState) attributes suggested:
    - `name` — for greeting node input.
    - `numbers` (a list) — to store generated random numbers.
    - `counter` — to track how many random numbers have been generated and when to stop.
  - Practical advice:
    - When designing AI agents, you may not know all attributes ahead of time; practice improves your ability to plan attributes.

- Node behavior details:
  - Greeting node:
    - Define a function that accepts the agent state and updates the `name` key to say `"Hi there, state.name."`.
    - Initialize the `counter` variable here; start it at zero if the user provides a negative integer to make the flow more robust.
  - Random node:
    - Generate a random number from 0 to 10.
    - Append the generated number to the `numbers` list in the state.
    - Increment the `counter` value after appending the number.

### Greeting and Random Nodes

- Building the greeting and random nodes and implementing looping:
  - Greeting node:
    - Define a function that takes the agent state and sets the `name` key to `"Hi there, state.name."`.
    - Initialize the `counter` here; ensure that if the user passes a negative integer the counter starts at zero for robustness.
  - Random node:
    - Generate a random integer between 0 and 10.
    - Append that random number to the state's number list.
    - Increment the `counter` after each generation.

- Loop control logic:
  - Implement a function called `should_continue` to decide the next edge.
    - If `counter < 5`, return the loop edge (to re-enter the random node) and the exit edge.
    - Once the counter reaches five iterations, the conditional will fail and the else branch should return the exit edge.
  - Intended trajectory:
    1. Start at the greeting node.
    2. Enter the random node.
    3. Repeat the random node five times (via the loop edge controlled by `should_continue`).
    4. After five iterations, follow the exit edge to the endpoint.

- Implementation note:
  - There are multiple ways to implement loops in software and in Langraph; this demonstrates one graph-based approach to looping for clarity and practice.

### Loop Control Function

• Implementation overview:
  - There are multiple ways to code an application; the same applies to Langraph.
  - The instructor will show one way to create a loop.

• Loop decision function:
  - Create a function named `should_continue` to decide routing.
  - Behavior specified: if the counter value is less than five, `should_continue` will return the loop edge and the exit edge.

• Intended trajectory of the loop:
  1. Start at the greeting node.
  2. Enter the random node.
  3. Exit the random node five times.
  4. After five iterations the `if` condition will fail, and the `else` branch will return the exit.

• Quick graph construction steps:
  1. Initialize the graph.
  2. Add two nodes: `greeting` and `random`.
  3. Create an edge between the `greeting` and `random` nodes.

### Graph Construction and Conditional Edges

• Continuing graph construction:
  - Initialize the graph and add the nodes `greeting` and `random`.
  - Create the conditional edges with `random` as the source node and the routing function `should_continue`.

• Routing behavior for the conditional edge:
  - If the loop is outputted, route back to the `random` node.
  - If not, route to the endpoint.

• Finalizing the graph:
  - Set the entry point and compile the graph.
  - The compiled graph should match the intended structure (an image was referenced for comparison).

• Example run and code notes (speaker's code):
  - The speaker set their name, initialized a new list, and set the counter to `-1`.
  - The output shows the greeting and the generated random numbers.
  - The counter value is five; the speaker notes that if they had not set it to zero it would have generated six times.
  - The speaker states this is their personal approach to creating loops in Langraph and that with practice you may find other ways.

### Example Run and Notes

• Example run details (reiterated):
  - In the provided code the speaker set their name, initialized a new list, and set the counter to `-1`.
  - The program output shows the greeting and the generated random numbers.
  - The counter value is five; the speaker notes that without setting it to zero it would have generated six times.

• Exercise status:
  - This is the final code for the last graph of the section.
  - The speaker asks the listener to complete the Graph 5 exercise.

### Exercise: Higher or Lower Game

• Exercise: Automatic Higher-or-Lower game requirements:
  - Implement an automatic higher-or-lower guessing game.
  - Bounds: integers between 1 and 20.
  - Maximum guesses: seven.
  - Behavior: if a guess is correct, stop; otherwise keep looping until the limit is reached.

• Automation and hints:
  - The graph should automatically guess without human intervention.
  - Each guessed number should trigger the hint node to say either "higher" or "lower." The graph should adjust its guesses accordingly.

• Required input/state for the graph:
  - Player name.
  - An empty list for guesses.
  - `attempts` set to zero.
  - Bounds of 1 to 20 (to allow easy expansion of the range).

• Learning objective and follow-up:
  - Completing this exercise reinforces understanding of loops in Langraph.
  - Cross-reference your answers on GitHub.
  - The instructor will continue in the next section where AI agents are introduced.

## Environment and Basic LLM Agent

### .env File

• Purpose of a `.env` file:
  - A `.env` file is used to store sensitive information such as API keys or configuration values.
  - Its primary purpose is security (to keep secrets hidden).

• Practical note from the speaker:
  - The speaker keeps a `.env` file in their folder structure to hide their API key, since exposing it could lead to financial loss.

• Why an API key is needed here:
  - An API key is required because the code makes calls to an external large language model (LLM) hosted on a cloud service.
  - If using your own LLM via an integration (for example, the OpenAI library with LangChain), you would not need an external API key in the same way.
  - Because an external service is used, an API is required to communicate with the LLM on their cloud servers.

• Loading the API key in Python:

```python
load_dotenv()
```

### Agent State for LLM

• Defining the agent state:
  - Create a class called `AgentState` as a typed dictionary.

• Required attributes for this simple agent state:
  - The attributes are minimal; the primary required attribute is `messages`.
  - `messages` should be a list of human messages.
  - Specify that these messages are of type `HumanMessage`.

### Initialize LLM

• Initializing the LLM:
  - Instantiate the model with `lm = ChatOpenAI()` and specify the model to use; the speaker will be using GPT-4.
  - Other available models mentioned include ChatAnthropic and ChatOpenAI.
  - The speaker prefers `ChatOpenAI` for its straightforward usage and notes having tried `ChatOAI` but encountered integration difficulties with LangChain.

• Cost considerations:
  - The speaker reassures that costs are affordable and mentions the option of using the GPT-4 mini model if cost is a concern.
  - Input and output tokens are described as being priced in pennies for thousands of tokens.

• Defining node behavior and invoking the LLM:
  - Define a node through a function called `process` where you will define and return the state.
  - LangChain/LangGraph terminology: to call the LLM use the term "invoke."
  - Call the model with `lm.invoke()` and store the response in a variable.
  - The `invoke` method requires a `LanguageModelInput` that specifies what you want the LLM to do; supply the messages as `state.messages`.
  - The generated response from the LLM will be stored in the `response` variable.

### Process Node and Invoke

• `process` node and invoking workflow:
  1. Define a function named `process` that defines and returns the `state`.
  2. Invoke the LLM using `lm.invoke()`, which accepts a `LanguageModelInput`.
  3. Pass `state.messages` as the messages input to the `invoke` method so the LLM can generate a response from its cloud server.
  4. Store the result in a `response` variable.
  5. Print the response and return the state.

• Graph creation summary:
  - Create the graph with the `process` node (the node where action occurs).
  - Add an edge from the start to the endpoint and compile the graph.

### Run Example and Loop

• Asking for user input and running the agent:
  - Example code to get user input: `user_input = input("Enter something: ")`.
  - Because this is a graph-based agent, you must invoke the agent with the input.

• Example runs and observations:
  - Running `python agentbot.py` and entering "hi" yields the AI response: "Hello, how can I assist you today?"
  - The speaker confirms this is generated by the LLM and not pre-coded.
  - Running the program again and asking "Who are you?" yields: "I'm an AI language model created by OpenAI called ChatGPT."
  - These results confirm the LLM is functioning correctly.

• Extending to multiple messages (chat behavior):
  - Modify the code to iterate through user input until the user types `"exit"`, at which point break the loop.
  - With the updated code, running `python agentbot.py` allows continued conversation (examples: "Who made you?", "What is 2 + 2?").

• Limitation of the simple bot:
  - If you ask, "What is my name?" the AI replies it cannot know personal information because no memory has been implemented.
  - Therefore, this implementation is a simple bot (an LLM wrapper), not yet an agent with memory.

• Practical notes:
  - Integrating LLMs into graphs is straightforward; the code is around 25–29 lines.
  - There are no exercises for this section.

## Chatbot with Memory

### Goals and Imports

• Goals for the next system:
  - Build a second AI system to address the previous system's limitation: lack of memory.
  - Create a chatbot that can remember previous interactions.

• Objectives for this subsection:
  - Use different message types: human and AI messages.
  - Maintain a full conversation history.
  - Use GPT-4 with LangChain's `ChatOpenAI` to create a more sophisticated conversation loop.
  - The main goal is to create a form of memory for the agent.

• Setup notes and imports:
  - Imports are largely the same as before, with two additions: the AI message type and the `Union` type annotation.
  - `Union` allows a variable to hold multiple types of data; review the first chapter if unfamiliar.

• State definition reminder:
  - Define the state again as a class called `AgentState`, a typed dictionary.

### State with Union and Messages

• Message types in the state:
  - Previously the state contained only a list of human messages.
  - Now include AI messages as well to support a memory-capable chatbot.

• Using `Union` to simplify state structure:
  - Instead of separate lists for human and AI messages, use the `Union` type annotation to allow both types in a single list.
  - Human and AI messages are built-in data types within LangGraph and LangChain.

### Model and Node Behavior

• Libraries and approach:
  - Although you can build an agentic system using plain Python functions, the speaker recommends using libraries like LangGraph for a balance of control and simplicity.

• Model and node setup:
  - Initialize the LLM again using GPT-4.
  - Create a node with the same graph structure as before but with modified actions.
  - Add a docstring for the node stating it will solve the input request.

• Message handling and state updates:
  - Invoke the LLM with the `state` messages, which may include human or AI messages.
  - Extract the AI message content from the response and append it to the state messages.
  - Print the state for readability in the terminal and return it.

• Conversation loop and history:
  - Initialize a conversation history to track the dialogue.
  - Use a `while` loop to ask the user for requests; continue until the user types `"exit"`.
  - Update the conversation history with each human message (the user's input).
  - Invoke the compiled agent (graph) with the entire conversation history, not just the current human message, so the agent can remember prior interactions and produce more coherent responses.

### Run Demo and Observe Memory

• Post-processing and state replacement:
  - After processing input, replace the conversation history with the result messages.

• Running the memory-enabled agent:
  - Execute `python memory_agent.py` to test the chatbot's memory.

• Example interaction demonstrating memory:
  1. User: "Hi, my name is Steve."
     - AI responds: "Hi Steve, it's great to meet you. How can I help you today?"
  2. User: "What is my name?"
     - AI responds: "You are Steve."
  - This demonstrates the agent remembering previous context.

• Observability and debugging:
  - Add print statements to visualize how the conversation history evolves.
  - After running the program and entering various messages, observe how the state changes and how the AI responds.

### Limitations and Solutions

• Two significant limitations of the simple memory implementation:
  1. Persistence across runs:
     - Problem: exiting the program loses the conversation history.
     - Simple solution: store the conversation history in a text file for prototyping.
     - More robust solution: use a database.
     - Implementation note: saving involves creating a text file and writing each message with a distinction between human and AI messages.
     - After running the program and inputting messages, you can check the text file to see the logged conversation.

  2. Growing state size and cost:
     - Problem: as the conversation continues, the state length increases and consumes more tokens, increasing LLM costs.
     - Potential solution: limit the number of human messages stored in the conversation history (example given: if messages exceed five, remove the oldest message).
     - This helps manage costs while preserving relevant context.

### Section Summary

• Section summary:
  - You have learned how to integrate human and AI messages into a chatbot to create a more sophisticated system with memory.

• Next step:
  - The next agent to build will be a React agent (reasoning and acting).

## React Agent and Tools

### Introduction

• Introduction to the React agent and tools:
  - The upcoming agent type is called a React agent, standing for reasoning and acting.
  - This type of agent is common in AI development; the section will cover how to create tools in LangGraph.

• Objectives for this section:
  - Build a React graph.
  - Work with different types of messages.
  - Test the robustness of the graph.

• Note on scope:
  - The section will include numerous imports; the speaker will explain each line.

### Typing: Annotated & Sequence

• Typing imports and brief explanations:
  - The first import line brings in `Annotated`, `Sequence`, and `TypedDict` from the `typing` module.

• `Annotated`:
  - `Annotated` provides additional context (metadata) for a variable or key without changing its data type.
  - Example intent: a `TypedDict` key `email: str` can be annotated to indicate it must follow a particular email format while still being a `str`.
  - The speaker demonstrates that the annotation metadata can be accessed (for example, `print(email.metadata)` to see the note that it must be a valid email format).

• `Sequence`:
  - `Sequence` is a type annotation that helps handle state updates for sequences (for example, adding new messages to chat history).
  - It reduces the need for manual list manipulation when nodes update sequence-like state.
  - The speaker notes this helps when using graphs and nodes that update lists frequently and says you "don't need to worry about it too much."

### Env and Message Types

• Environment and message-type imports:
  - Import `env` from `loadenv` to load API keys (as done previously).

• New message types being imported:
  - `base message`, `tool message`, and `system message`.

• `tool message`:
  - A `tool message` is used when data is passed back to the language model after a tool has been called.
  - Information included: the content and the tool call ID.

• `system message`:
  - A `system message` provides instructions to the LLM (example: "You are a helpful assistant").

• `base message` and class hierarchy:
  - `base message` is the foundational class for all message types in Langraph.
  - Child classes (AI message, human message, tool message, system message, etc.) inherit properties from `base message`.
  - Each child class (for example, `tool message`) has its own properties such as content and tool call ID.

• Other imports noted:
  - `chat` from `openAI`, and familiar items `state`, `graph`, and `M`.

### Reducer Functions

• Additional imports for tools and reducers:
  - `tool` and `tool nodes` are imported (to be covered in a later chapter).
  - `from langraph.dosage import add_messages` imports a reducer function named `add_messages`.

• Reducer functions explained:
  - A reducer function defines how updates from nodes are combined with the existing state.
  - In other words, it controls how to merge new data into the current state rather than overwriting it.
  - Without a reducer, updates would replace the existing value.

• Example motivation:
  - If the state has `messages = "hi"` and an update arrives with "nice to meet you," without a reducer the update would overwrite the existing state.
  - Previously we appended messages; with many message types and tool calls, indiscriminate appending or overwriting becomes impractical.

• Purpose of `add_messages`:
  - `add_messages` is a reducer that aggregates data by appending messages instead of overwriting, preserving the existing state.

### State and Tool Creation

• Creating the React agent state:
  - Begin by creating the state for the agent; in this example there is only one key: `messages`.
  - Use the `sequence` type annotation, `base message`, and the reducer function `add_messages`.
  - This combination indicates the intent to preserve state by appending (via the reducer) rather than overwriting.
  - The `sequence` of `base message` provides the data type and metadata, which is why `Annotated` is used.

• Creating a tool:
  - Define a Python function and mark it with the appropriate decorator to indicate it is a tool.
  - Example tool signature described: `def add(a: int, b: int)` which adds two numbers.
  - Docstring for the tool: "This is an addition function that adds two numbers together."
  - The function returns `a + b`.

• Incorporating tools into the LLM:
  - After defining tools, create a list called `tools` to supply them to the LLM.

### Model Binding and Agent Node

- Tools
  - At the moment there is only one tool, but the plan is to support multiple tools; a list of tools is added for that reason.

- Model creation and binding
  - Create the model with:  
    ```
    model = chat.openAI
    ```
    - The model is set to `GPT-4` (the speaker chose GPT-4 because they have never had a problem with it).
  - Bind the tools to the LLM using the built-in Python function `bind_tools` and pass in the list of tools so the large language model has access to them.

- Agent node (model call)
  - Define a node that acts as the agent in the graph with a simple function:  
    ```
    def model_call(state: agent_state)
    ```
    - The function needs to return the agent state.
  - The code invokes the model, running it with the system message being asked. The LLM is explicitly told that it is the system and to answer the query to the best of its ability.
  - The system message example:  
    ```
    "You are my AI system. Please answer my query to the best of your ability."
    ```
    - The speaker notes an alternative variable name `system_prompt` could be used, but the chosen form is preferred for readability.

- State updates and response handling
  - Instead of writing `state['messages'] = something` you can write a more compact updated state; the example returns `messages_response`, updating the messages with the response.
  - The `add_messages` reducer function handles appending messages so it doesn't overwrite the state.

- Important invocation detail (must pass the query)
  - The earlier code would not work because when invoking the model and storing the response the query was not passed in.
  - To add the query use:  
    ```
    state['messages'] = human_message
    ```
    - The human message will be stored in the `messages` attribute.
  - Once the human message is passed into the model, invoking it should work.

### Conditional Edge and Looping Tools

- Purpose of the conditional edge
  - The conditional edge is needed because the looping part of the graph uses a conditional edge; it determines whether the graph continues to call tools or ends.

- Conditional edge function
  - Define the conditional edge as:  
    ```
    def should_continue(state)
    ```
    - The function takes the state and returns `continue` when appropriate.
  - When the query is passed in and the model is invoked, a list of tools will be created and the last message examined to see if any more tools need to run.

- Loop behavior
  - If more tool calls are needed: follow the `continue` edge, select the tool, perform the actions, then return to the agent.
  - If there are no more tool calls: end the graph.

- Graph nodes and edges (structure)
  - Initialize the graph through `state_graph` and create the agent node named `R_agent` whose action is the model call function.
  - Create a tool node containing all tools (currently only `add`).
  - Set the entry point to `R_agent`.
  - Add the conditional edge from the agent: it directs either to the tool node or to the endpoint. The conditional edge is a one-way directed edge from the agent to the tool node or the endpoint.
  - Add an edge from the tool node back to the agent to create a circular connection (the tool-to-agent return edge is required in addition to the agent-to-tool conditional edge).

### Graph Assembly and Compile

- Graph definition (assembly)
  - Initialize the graph through `state_graph` and add the agent node `R_agent` with the model call function as its action.
  - Create a tool node that contains all tools (the example has a single tool: `add`).
  - Set the entry point to `R_agent`.
  - Add the conditional edge from the agent that either goes to the tool node or to the end; add the edge from the tool node back to the agent to create a loop.

- Compile the graph
  - After assembling the nodes and edges, compile the graph with:  
    ```
    app = graph.compile()
    ```

### Helper and Examples

- Helper function
  - A new helper function (not part of Langraph) was created to make tool calling and output formatting much better.

- Example usages (streaming and tool selection)
  - Example input and streaming call: `"add 3 + 4."` — this line of code streams the data.
  - When invoked with `"add 3 + 4"` it calls the tool, selects the correct tool, and returns the result.
  - The tool message shows the result as `7`, and the final AI message states:  
    `"The sum of three and four is seven."`

- Additional examples
  - Example: `"add 34 + 21."` — the result is `55` as expected.

- Docstring requirement
  - If the docstring is removed (for example by commenting it out), an error occurs because the function must have a docstring.
  - The docstring is necessary; it tells the LLM what the tool is for and without it the graph won't work.

- Loop demonstration
  - Executing both commands `"add 34 + 21"` and `"add 3 + 4."` shows the tool being called twice, demonstrating the loop's behavior.

### Extend Tools and Complex Commands

- Extending tools
  - Add more tools such as `subtract` and `multiply` and include them in the tools list.

- Behavior with multiple tools
  - Running the same commands shows the system handles multiple tools without confusion.

- Complex command example
  - Example command:  
    `"add 40 + 12 and then multiply the result by 6."`
  - The LLM first uses the `add` tool, then the `multiply` tool, returning the final answer `312`.

- Non-tool commands
  - Example: `"tell me a joke."` — the LLM handles this gracefully, providing a joke after performing calculations if any were requested.

- Demonstration of robustness
  - These examples demonstrate Langraph's ability to handle queries that do or do not require tools.

### React Agent Summary

- Key takeaways about the react agent
  - You now know how to create a react agent.
  - The example was a simple react agent, but the concepts generalize: you can create external tools and graphs.
  - The goal of the course section was to understand how to create and use these tools.
  - The instructor will continue in the next subsection.

## Drafter Project

### Project Overview

- Progress and next section
  - The course has made significant progress so far.
  - The next section will build a fourth AI agent, done slightly differently from previous agents.

- Project: "Drafter"
  - Mini project name: "Drafter."  
  - Scenario: in a company that wastes time drafting documents, the boss wants an AI agentic system to speed up drafting documents and emails.

- Requirements for the AI agentic system
  - Support human–AI collaboration: the human can provide continuous feedback and the AI should stop when the human is satisfied with the draft.
  - Be fast and able to save drafts.

- Graph sketch for Drafter
  - The sketch will have a start and an endpoint; the agent will have access to tools including a save tool.
  - The save tool will save the draft and once it is saved the process should end.

### Global Variable Strategy

- Difference from the react agent
  - This Drafter design differs from the react agent because tools do not always return to the AI agent in the same way.

- Setup notes
  - The instructor has already done all imports and loaded the environment file; these imports were encountered earlier and are not re-explained.

- Global variable strategy (workaround)
  - The first code step is to define a global variable.
  - Defining global variables is acknowledged as odd, but it is used here to correctly pass state into tools.
  - The proper Langraph approach is "injected state," which is beyond the course scope; as a workaround the global variable is used and any updates update that variable.
  - When saving, the save tool will use the contents of this global variable to save into a text file.

### Agent State and Tools

- Agent state definition
  - The agent state is defined similarly to before:  
    ```
    class agent_state(messages: annotated[sequence[base_message]], add_messages: reducer_function)
    ```

- Tools overview
  - Two tools will be provided: `update` and `save`.

- Update tool
  - Define the update tool using the decorator and a function signature like:  
    ```
    def update(content)
    ```
  - The `content` parameter is provided by the LLM in the background.
  - The docstring will state that this updates the document with the provided content.
  - The update tool will interact with the global variable, updating the document content and returning a statement to the LLM that the document has been updated successfully.

- Save tool
  - Define the save tool with the decorator and request a file name from the LLM.
  - The save tool handles the save logic; the docstring will state that it saves the current document to a text file and finishes the process.
  - The file-name argument should end with `".txt."` If it doesn't, the code will append `".txt"` to ensure robustness.
  - The save tool calls the global variable to get the content and saves the contents under the specified file name (this piece of code is not part of Langraph; it performs the actual file write).
  - An exception has been added for debugging purposes to identify any errors.

- Tools list
  - Create a list of tools that includes the `update` and `save` tools.

### Model, System Prompt, and Robustness

- Model and tool binding
  - After calling the model, remember to bind the tools; binding is required for the LLM to use the tools.

- Agent initialization and function
  - Initialize the agent as a node in the graph with a function signature:  
    ```
    def r_agent(state: agent_state)
    ```

- System prompt (content and instructions)
  - A system message is provided; the system prompt content example:  
    ```
    "You are Drafter, a helpful writing assistant. You will help the user update and modify documents."
    ```
  - The prompt also includes instructions on how to use the `update` and `save` tools and a requirement to always show the current document after modifications.

- Robustness measures at initialization
  - On first initialization, ensure everything is set up correctly and handle empty-state behavior:
    - If `state.messages` is empty, do not ask how the user would like to change the document (there is no document yet). Instead provide an introductory message such as:  
      `"I'm ready to help you update a document. What would you like to create?"`  
      - This collects the user's input and stores it as a human message in the user message variable.
    - If there is already a message (i.e., a document exists or is being updated), use an else branch that asks:  
      `"What would you like to do with the document?"`  
      - This assumes content exists in `state.messages` and prompts the user on how to update it.
    - The user input is printed (under an emoji in the terminal) so the user can see what they inputted, and it is stored as the user message.

- Invoking the model and returning state
  - Combine messages (system prompt, state messages, and the new user message to update) and then invoke the model using the model-invoke function.
  - The function includes print statements for terminal aesthetics: showing the AI response and tool messages.
  - Return the updated state; the instructor notes a concise state-update style shown previously will be used from now on.

- Conditional edge function
  - Create a conditional edge function to determine if the conversation should continue or end. If there are no messages, the graph should continue rather than end — this is a robustness measure.

### Conditional Edge: Continue vs End

- Conditional edge behavior: continue vs end
  - The conditional edge function checks the most recent tool message to determine whether to continue or end.
  - If the `save` tool was used: end the program.
  - If the `update` tool was used: continue the loop.
  - Thus, to continue you must use the `update` tool; to end you must use the `save` tool.
  - Print statements can be added to clarify the workflow during execution.
  - The function returns `continue` when the logic determines the conversation should proceed (e.g., when the save tool was not the last tool used).

### Formatting, Graph Build, Run

- Print formatting helper
  - Create a function to format print statements for more readable terminal output; this helps when invoking the graph and monitoring the process.

- Graph build (nodes and edges)
  - Initialize the graph through a `state_graph` and add nodes for the agent and tools (tools are grouped into a tool node).
  - Set the entry point to the agent (starting point), then add a directed edge between the agent and tools.
  - Add the conditional edge that connects the tools to the continue and end options; together these directed edges form the loop for human–AI collaboration.
  - Compile the graph once structure is complete.

- Compact invocation function
  - A compact function is provided to invoke the graph and facilitate human–AI collaboration.

- Use of global variable
  - The design uses a global variable as a workaround; while some may disapprove, it is acceptable for this beginner-level course. A proper Langraph implementation would use injected state for more complex features.

- Run example and interactive flow
  - Run the program with:  
    ```
    python draft.py
    ```
  - The program prompts what you would like to add or create in the document. Example interaction:
    - Input: `"Write me an email to Tom saying I cannot make it to the meeting."` — the AI responds with a draft email.
    - Provide feedback to improve the email, for example: specify the meeting time and location such as `10:00 a.m. in Canary Wharf` and the AI updates the email.
    - Change the sender name by specifying `my name is V` and the AI updates the draft accordingly.
    - Add meeting availability such as `I can meet at 12:00 p.m. in New York the next day` and the AI updates the draft.
    - After edits, request the AI to save the document; the AI will call the `save` tool, update the document, display the current content, and save it with a generated filename.

- Additional behaviors and robustness
  - You can pass in a previous message to start with a non-empty initial state; starting with an existing document lets the model know current content and how to change it.
  - The system handles incomplete input by prompting for more details.
  - The agent node has an LLM in the background and `bind_tools` expands its capabilities by providing tools; the LLM does not have to use the tools if unnecessary.

### Extensions and Notes

- Possible extensions
  - Add a voice feature using OpenAI Whisper for speech-to-text or Eleven Labs for text-to-speech.
  - Implement a GUI.
  - Integrate a knowledge base.

- Next agent
  - The next step is to build a fifth AI agent focused on retrieval-augmented generation (RAG). The RAG graph will have a start and end point and include two agents: a retriever agent and the main LLM agent.

## RAG Agent (Retrieval-Augmented Generation)

### RAG Overview

- RAG agent overview
  - Build a fifth AI agent focused on retrieval-augmented generation (RAG); the graph will have a start and an endpoint, with two agents: a retriever agent and the main LLM agent.
  - The instructor will not deeply explain RAG theory, only a surface-level explanation before jumping to code.

- Setup notes
  - Four new imports are required (these will be explained as they are used).
  - Load the environment file containing API keys and initialize the LLM with a `temperature` parameter.

- Temperature parameter
  - `temperature` controls model stochasticity: `0` makes outputs more deterministic; `1` makes outputs more stochastic.

- Embedding model
  - Create an embedding model to convert text into vector embeddings.
  - The embedding model must be compatible with the LLM; incompatible embedding/LLM pairs can fail due to differences in vector dimensions (the instructor gives an example involving a "GBD40 model" and an embedding model from a different source leading to incompatibility).

### Embeddings and Document Loading

- Document specification
  - Specify the PDF document containing stock market performance data for 2024; the document has nine pages and various details about the stock market.

- Loader behavior and debugging
  - If the PDF is in the wrong directory or cannot be found, an error will be raised for debugging purposes; the PDF loader will load the document and the code will check how many pages it contains.

- Chunking configuration
  - Chunking divides the document into manageable pieces with:
    - chunk size = `1,000` tokens
    - chunk overlap = `200` tokens
    - Consecutive chunks share overlap tokens to retain context.
  - Apply the chunking process to all nine pages of the document.

- Vector database (Chroma)
  - Use the Chroma vector database to store vector embeddings and specify the file path and collection name for the database.
  - If this is the first time running, create the collection in the specified directory.
  - A try-except block handles creation of the vector embedding database and parameters such as how to split pages and where to store them.

### Chunking and Vector DB

- Chunking recap
  - Chunking divides the document into pieces with `chunk_size = 1,000` tokens and `chunk_overlap = 200` tokens so consecutive chunks share context.
  - The chunking is applied across all nine pages; embeddings for the chunks are stored in the Chroma vector database with a specified file path and collection name.
  - If running for the first time, the code creates the collection in the specified directory inside a try-except block.

- Retriever and returned chunks
  - The retriever is responsible for returning the most similar chunks for a query; set the number of returned chunks to `5` as a middle ground.

- Retriever tool
  - Create a tool via the decorator that takes a query and returns a string.
  - If no relevant information is found for the query, the tool returns a message indicating this.
  - If relevant chunks are found, they are stored in a list and returned in the results.

### Retriever Tool

- Retriever binding and agent state
  - Bind the retriever tool to the LLM and create the agent state.
  - The `should_continue` function will check whether the last message contains any tool calls to decide whether to proceed or end.

- System prompt and hallucination mitigation
  - Provide a detailed system prompt that instructs the LLM on how to respond accurately and to minimize hallucinations.

- Tools dictionary and LLM agent function
  - Create a dictionary of tools and define the underlying function for the LLM agent that calls the LLM with the current state and returns updated messages.

- Retriever agent behavior and tool execution
  - The retriever agent executes tool calls from the LLM response, checks if the tool name is valid, and invokes it if valid.
  - If the tool name is not valid, the retriever agent will prompt the user to retry with a valid tool.

### Graph Assembly and Test

- Binding and graph assembly
  - Bind the retriever tool to the LLM and create the agent state.
  - Provide a system prompt to guide the LLM and reduce hallucinations.
  - Create a dictionary of tools and define the LLM agent function that calls the LLM with the current state and returns updated messages.

- Retriever agent execution
  - The retriever agent will execute tool calls from the LLM response, validating tool names and invoking valid tools; otherwise it asks the user to retry.

- Graph initialization and compilation
  - Initialize the graph, add the two AI agents as nodes (retriever agent and main LLM agent), and create the conditional edge.
  - Set the entry point and compile the graph to store it in the RAG agent.

- Query loop function
  - Create a function that allows asking questions to the graph and receiving answers; exit the loop by typing `"exit"` or `"quit."`

### Run Demo and Results

- Running the RAG demo
  - Run the demo with:  
    ```
    python rag_agent.py
    ```
  - The PDF will load and the Chroma vector database will be created.

- Example queries and behavior
  - Example: ask how the S&P 500 performed in 2024 — the system calls the retriever tool and returns relevant information with citations from the document.
  - If you ask about a topic not covered in the document (for example, OpenAI's performance in 2024), the system will correctly indicate there is no relevant information.

- Conclusion about RAG setup
  - These behaviors demonstrate the RAG setup is functioning correctly. The instructor concludes the course and notes there are many more AI projects possible with Langraph.

## Conclusion

- Closing and contact
  - If you have any questions or want to connect, feel free to reach out on LinkedIn.
  - Thank you for watching; the instructor hopes to see you in another course.
