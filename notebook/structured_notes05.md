# Langraph Course Notes

## Course Overview

- Langraph is a Python library for building advanced conversational AI workflows.
- The course teaches how to design, implement, and manage complex dialogue systems using a graph-based approach.
- The goal is to build robust, scalable conversational applications that leverage the full potential of large language models.
- The course is intended for learners who may know of Langraph but have not coded in it before.
- Explanations are intentionally detailed and may move slowly at times.
- The course includes:
  - Building graphs
  - Building AI agents
  - Learning theory
  - Exercises throughout the course
- Answers to exercises are provided on GitHub.

---

## Section 1: Type Annotations

### Purpose of This Section

- This section is theoretical and short.
- It is included because type annotations appear frequently when coding graphs, AI agents, and Langraph workflows.
- The goal is to ensure these concepts are familiar before they appear in code.

### Dictionaries

#### Standard Dictionary

- Dictionaries are a data structure.
- Example structure:
  - Key: `name`
  - Key: `year`
  - Value: `Avengers Endgame`
  - Value: `2019`
- Dictionaries are useful because they:
  - Allow efficient data retrieval based on unique keys
  - Are flexible
  - Are easy to implement
- Problem:
  - They do not enforce a particular data structure
  - They do not check whether the data has the correct type or structure
  - This can lead to logical errors, especially in large projects
  - These errors can be difficult to identify because the issue may be small and hidden

#### Typed Dictionary

- The solution is a type dictionary.
- A type dictionary is implemented as a class.
- It defines the expected data type for each key.
- Example structure:
  - `name`: string
  - `year`: integer
- The same dictionary example is used, with the same keys and values:
  - `name`
  - `year`
  - `Avengers Endgame`
  - `2019`
- Benefits:
  - Type safety
  - Reduced runtime errors
  - Improved readability
  - Easier debugging
- Type annotations are used extensively in Langraph.
- They are used to define states.

### Union

- Union is a type annotation.
- It specifies that a value can be only one of a defined set of types.
- Example:
  - A function squares a value.
  - The input `x` can be either an integer or a float.
- Valid inputs:
  - `5`
  - `1.234`
- Invalid input:
  - A string such as `I am a string`
- In more complicated applications, Union is useful for type safety and for catching incorrect usage.
- The makers of LangChain and Langraph used Union extensively in the library.
- It is flexible and easy to code.

### Optional

- Optional is similar to Union.
- Example:
  - A function `nice_message` takes a `name`.
  - If a name is passed in, it says: `hi there name`
- Example:
  - If the name is `Bob`, it says: `hi there Bob`
- If nothing is passed in:
  - Optional allows the value to be either a string or `None`
  - The function outputs: `hey random person`
- The value cannot be anything else.
- It cannot be:
  - An integer
  - A boolean
  - A float
  - Anything other than a string or `None`

### Any

- `Any` means the value could be anything.
- It can be any data structure.
- Example:
  - A function `print_value` takes something and prints it.
  - A string can be passed in and printed.
- Everything is allowed.

### Lambda Functions

#### Definition

- Lambda functions are useful shortcuts for writing small functions.

#### Example 1

- A square function takes a number and squares it.
- Example:
  - `square(10)` gives `100`

#### Example 2

- A lambda function can be used with `map`.
- Example input:
  - `1, 2, 3, 4`
- The code squares each number in `nums`.
- `map` applies the function to each value.
- The result becomes:
  - `1, 4, 9, 16`
- Lambda functions are a shortcut for small functions.
- They make code efficient.
- A beginner programmer might use a for loop.
- A more advanced programmer might use the lambda-based approach.

---

## Section 2: Core Elements in Langraph

### State

#### Definition

- State is one of the most fundamental elements in Langraph.
- It is a shared data structure that holds the current information or context of the entire application.
- It functions like the application's memory.
- It keeps track of variables and data that nodes can access and modify as they execute.

#### Analogy

- Whiteboard in a meeting room:
  - The whiteboard represents the state.
  - Participants represent nodes.
  - New information or updates are written on the whiteboard.
- The state shows the updated content or information of the entire application.

### Node

#### Definition

- A node is one of the most fundamental elements in Langraph.
- Nodes are individual functions or operations that perform specific tasks within the graph.
- A node:
  - Receives an input, often the current state
  - Processes it
  - Produces an output or updated state

#### Analogy

- Assembly line station:
  - Each station does one specific job
  - Examples of jobs:
    - Attaching a part
    - Painting
    - Inspecting quality
  - Each station represents a node because it performs one specific task

### Graph

#### Definition

- The graph is the overarching structure in Langraph.
- It maps how different tasks, or nodes, are connected and executed.
- It visually represents the workflow.
- It shows:
  - The sequence of operations
  - Conditional parts between operations

#### Analogy

- Road map:
  - Different routes connect cities
  - Intersections offer choices on which path to take next

### Edges

#### Definition

- Edges are the connections between nodes.
- They determine the flow of execution.
- They specify which node should be executed next after the current one completes its task.

#### Analogy

- Train track:
  - The track is an edge
  - It connects two stations, which represent nodes
  - It connects them in a specific direction
  - The train represents the state
  - The state moves and gets updated from one station to another

### Conditional Edges

#### Definition

- Conditional edges are specialized connections.
- They decide the next node to be executed based on a specific condition or logic applied to the current state.

#### Analogy

- Traffic light:
  - Green means go one way
  - Red means stop
  - Yellow means slow down
- The condition decides the next step.
- Another way to understand it is as an if-else statement.

### Start Point / Start Node

#### Definition

- The start point, or start node, is a virtual entry point in Langraph.
- It marks where the workflow begins.
- It does not perform any operations itself.
- It is the designated starting position for the graph's execution.

#### Analogy

- Starting line of a race

### End

#### Definition

- The end node signifies the conclusion of the workflow in Langraph.
- When the application reaches this node, the graph's execution stops completely.
- It indicates that all intended processes have been completed.

#### Analogy

- Finish line in a race

### Tools

#### Definition

- Tools are specialized functions or utilities that nodes can utilize to perform specific tasks.
- Example:
  - Fetching data from an API
- Tools enhance the capabilities of nodes by providing additional functionality.

#### Difference Between a Tool and a Node

- Node:
  - Part of the graph structure
- Tool:
  - Functionality used within nodes

#### Analogy

- Toolbox:
  - Hammer for nails
  - Screwdriver for screws
- Each tool has a distinct purpose

### Tool Node

#### Definition

- A tool node is a special kind of node.
- Its main job is to run a tool.
- Example:
  - A tool node uses a tool whose job is to fetch data from an API
- It connects the tool's output back into the state so other nodes can use that information.

#### Analogy

- Assembly line:
  - The operator represents the tool node
  - The operator controls the machine, which is the tool
  - The results are sent back into the assembly line

### State Graph

#### Definition

- The state graph is an important element.
- It is one of the first elements encountered in practice.
- Its main purpose is to build and compile the graph structure.
- It manages:
  - Nodes
  - Edges
  - Overall state
- It ensures:
  - The workflow operates in a unified way
  - Data flows correctly between components

#### Analogy

- Blueprint of a building:
  - A blueprint outlines the design and connections within a building
  - A state graph defines the structure and flow of the workflow or application

### Runnable

#### Definition

- A runnable is a standardized executable component that performs a specific task within an AI workflow.
- It is a fundamental building block for modular systems.

#### Difference Between a Runnable and a Node

- Runnable:
  - Can represent various operations
- Node:
  - Typically receives a state
  - Performs an action on it
  - Updates the state

#### Analogy

- Lego brick:
  - Lego bricks can be combined to build complicated structures
  - Runnables can be combined to create sophisticated AI workflows

### Message Types

#### Human Message

- Represents input from a user

#### AI Message

- Represents responses generated by AI models

#### System Message

- Used to provide instructions or context to the model

#### Tool Message

- Similar to the function message
- Specific to tool usage

#### Function Message

- Represents the tool of a function call

#### Familiarity from Other APIs

- If the learner has used a large language model API such as OpenAI's API, several of these message types may already be familiar:
  - System message
  - AI message
  - Human message

---

## Section 3: First Coding Phase

### Scope of This Section

- This section begins the coding portion of the course.
- The course will now start building graphs in Langraph.
- This section does not build AI agents yet.
- AI agents will be built later.

### Reason for Delaying AI Agents

- The course has not yet covered how to code in Langraph.
- Combining LLM APIs, tools, and other components too early would be messy and confusing.
- The course is designed to be beginner-friendly, detailed, and comprehensive.
- The approach is to proceed step by step.

### Purpose of This Phase

- Build a couple of graphs
- Understand Langraph better
- Learn the syntax better
- Learn how to code graphs
- Gain confidence with graph construction
- Move to AI agents after that