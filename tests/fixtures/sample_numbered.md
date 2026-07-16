1. TypedDict defines state shape.
2. State is passed to nodes.
3. Nodes update state.
4. Nodes never mutate state directly.
5. All fields are optional in total=False.
6. START connects to the first node.
7. Edges define execution order.
8. Conditional edges route on state values.
9. END terminates the graph.
10. Checkpointer persists state between runs.
