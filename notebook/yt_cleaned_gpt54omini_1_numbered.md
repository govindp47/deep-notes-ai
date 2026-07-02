1. Welcome to this video course on Langraph, the powerful Python library for building advanced conversational AI workflows.
2. In this course, Vbeca will teach you how to design, implement, and manage complex dialogue systems using a graph-based approach.
3. By the end, you'll be equipped to build robust, scalable conversational applications that leverage the full potential of large language models.
4. My name is Vava, and I'm a robotics and AI student.
5. In this course, we're going to be learning all about the fundamentals of Langraph.
6. I assume you've heard of Langraph before, hence why you clicked on this course.
7. I also assume you have never coded in Langraph before.
8. Because of this assumption, I have explained every single thing in as much detail as I possibly can.
9. This might mean that I will be going slow at times, so if you want, you can always speed me up.
10. In this course, we will be building a lot of graphs and AI agents.
11. We will learn a lot about the theory, and I have also provided exercises throughout the course, with all of the answers available on GitHub.
12. If you're ready to start this journey with me, let's go to our first section.
13. In this section, we will cover something called type annotations.
14. This will be a completely theoretical section, but it will be short and brief.
15. The reason I've included this specific section is that when we eventually code our AI agents and graphs in Langraph, these will start popping up everywhere.
16. I don't want you to start coding without having seen these before or without knowing what they actually are.
17. So, let's begin with dictionaries.
18. Dictionaries are a data structure, and there's a reason I've included it here.
19. In this case, I've described a very simple dictionary called movie, which has two keys: name and year.
20. It has two values: "Avengers Endgame" and 2019.
21. Dictionaries allow for efficient data retrieval based on their unique keys.
22. They are flexible and easy to implement, but there's a potential problem with them.
23. It can be a challenge to ensure that the data is of a particular structure, which could be a huge problem in larger projects.
24. In simple terms, dictionaries do not check if the data is the correct type or structure, which can lead to logical errors in your project.
25. If your project is large, this could be quite a headache to identify.
26. The solution for this is something called a type dictionary.
27. Here is an example of how to create a type dictionary in Python.
28. I want to emphasize that this type annotation is used extensively in Langraph to define states.
29. A type dictionary is easy to implement; you implement it as a class.
30. In this case, I've implemented the same example I showed you earlier, where I described the movie with the same keys and values.
31. Notice in this class, I have defined the actual data type of what each key should be.
32. For example, the name is a string, and the year is an integer.
33. To initialize a dictionary, I have done the same thing with "Avengers Endgame" and 2019.
34. There are two main benefits of using a type dictionary: type safety, because we've explicitly defined what should be in this data structure, which reduces runtime errors, and enhanced readability, making debugging easier if something goes wrong within this type dictionary.
35. Now we move on to another type of annotation, which is union.
36. You might have seen these later type annotations before if you have coded in Python, but I'm giving you a high-level overview of what they are.
37. Union specifies that a value can be either of the defined data types.
38. For example, I created a simple function that takes in a value and squares it.
39. The input x could be either an integer or a float, and union indicates that x can only be an integer or a float.
40. If I pass in 5 or 1.234, this would be fine, but if I pass in a string, it would fail.
41. This function is simple, but in more complicated applications, union is useful for type safety, helping to catch incorrect usage.
42. Another type annotation similar to union is optional.
43. Optional indicates that a parameter could either be a specific type or None.
44. For example, I described a function called nice_message that takes in a name.
45. If you pass in a name, it will say "Hi there, [name]."
46. If you don't pass in anything, optional indicates that the name parameter could either be a string or None.
47. If nothing is passed, it will say "Hey, random person."
48. It cannot be anything else; it must be either a string or None.
49. Now comes another type annotation called any, which means the value could be anything.
50. I created a simple function called print_value that takes in something and prints it.
51. For example, if I pass in a string, it prints it, and anything is allowed.
52. One last type annotation is the lambda function.
53. Lambda functions are useful for creating small functions efficiently.
54. For example, I created a square function that takes in a number and squares it.
55. If I pass in 10, it gives me 100.
56. Another example is using lambda with the map function to square each number in a list.
57. Lambda functions are shortcuts for writing small functions, making everything efficient.
58. You can see how powerful these type annotations are, and they will come up frequently.
59. You don't need to memorize this; just have a high-level overview of what they are.
60. Now, let's continue.
61. In this section, we will look at the different elements in Langraph.
62. The first element is the state.
63. A state is a shared data structure that holds the current information or context of the entire application.
64. In simpler terms, it is like the application's memory, keeping track of the variables and data that nodes can access and modify as they execute.
65. Think of the whiteboard in a meeting room as an analogy.
66. Each time you want to record or update information, you write it on the whiteboard, which acts as your state, while the participants act as nodes.
67. The state shows the updated content of your entire application.
68. Now, let's move on to the node, another fundamental element in Langraph.
69. Nodes are individual functions or operations that perform specific tasks within the graph.
70. Each node receives an input, often the current state of your application, processes it, and produces an output or an updated state.
71. An analogy for this is the assembly line station, where each station performs a specific job.
72. Each of these stations represents a node because they do one specific task.
73. To connect these different nodes together, we need to understand the graph.
74. The graph is the overarching structure that maps out how different tasks, or nodes, are connected and executed.
75. It visually represents the workflow, showing the sequence and conditional parts between various operations.
76. You can think of it as a roadmap, displaying different routes connecting cities with intersections offering choices on which path to take next.
77. Edges are the connections between nodes that determine the flow of execution.
78. They tell the application which node should be executed next after the current one completes its task.
79. An analogy for this is a train track connecting two stations, where the train represents the state being updated from one station to another.
80. There is also a type of edge called a conditional edge, which decides the next node to be executed based on specific conditions applied to the current state.
81. An analogy for this is a traffic light, where the light color decides the next step.
82. The start point, or start node, is a virtual entry point in Langraph that marks where the workflow begins.
83. It doesn't perform any operations itself but serves as the designated starting position for the graph's execution.
84. You can think of it as the starting line of a race.
85. The end node signifies the conclusion of the workflow in Langraph.
86. When the application reaches this node, the graph's execution stops, indicating that all intended processes have been completed.
87. You can think of it as the finish line in a race.
88. Tools are specialized functions or utilities that nodes can utilize to perform specific tasks, such as fetching data from an API.
89. They enhance the capabilities of nodes by providing additional functionalities.
90. The difference between a tool and a node is that a node is part of the graph structure, while tools are functionalities used within the nodes.
91. An analogy for this is tools in a toolbox, where each tool has a distinct purpose.
92. A tool node is a special kind of node whose main job is to run a tool.
93. For example, a tool node could be a node that uses a tool to fetch data from an API and connects the tool's output back into the state for other nodes to use.
94. The state graph is an important element that builds and compiles the graph structure.
95. It manages the nodes, edges, and overall state, ensuring that the workflow operates in a unified way and that data flows correctly between components.
96. You can think of it as a blueprint of a building, outlining the design and connections within the building.
97. A runnable in Langraph is a standardized executable component that performs a specific task within an AI workflow.
98. It acts as a fundamental building block, allowing us to create modular systems.
99. The difference between a runnable and a node is that a runnable can represent various operations, while a node typically receives a state, performs an action, and updates the state.
100. You can think of a runnable as a Lego brick, which can be combined to create sophisticated AI workflows.
101. Now let's move on to the different types of messages in Langraph.
102. The five most common message types are:
103. The human message, which represents input from a user.
104. The AI message, which represents responses generated by AI models.
105. The system message, which provides instructions or context to the model.
106. The tool message, which is specific to tool usage.
107. The function message, which represents a function call.
108. If you've used an API like a large language model API before, many of these will be familiar, especially the system message, AI message, and human message.
109. This concludes this section.
110. Now we are about to start coding in Langraph for the very first time.
111. Now that we've covered all the theory, we will code up some graphs.
112. We will code our very first graph in this subsection.
113. However, I have a slight confession: we are not going to be building any AI agents in this section.
114. This is because we haven't seen how to code in Langraph yet, and combining LLMs, APIs, and tools could be quite messy and confusing, especially since we have never coded in Langraph before.
115. This course is designed to be beginner-friendly, detailed, and comprehensive, and we will proceed step by step.
116. Don't worry; we will be coding AI agents soon.
117. For now, we will build a couple of graphs to understand Langraph better, the syntax, and how to code graphs confidently.
118. The graph we will build together is called the hello world graph, as it is the most basic form of a graph we can code in Langraph.
119. The objectives are to understand and define the agent state structure, create simple node functions, process them, and update the state.
120. We will build the first basic Langraph structure and understand how to compile, invoke, and process it.
121. The main goal of this section is to understand how data flows through a single node in Langraph.
122. The graph we will be building has a start point and an end point, with nodes sandwiched in between.
123. Now let's code this very first graph.
124. I have imported three main things: dict, type dict, and state graph.
125. The dict and type dict are dictionary and type dictionary, while state graph is a framework that helps you design and manage the flow of tasks in your application.
126. The first thing we will do after importing everything is create the state of our agent, which we will call agent state.
127. The state is a shared data structure that keeps track of all the information as the application runs.
128. We will build the agent state through a class.
129. Let's create a class called agent state, and the state needs to be in the form of a typed dictionary.
130. We will pass in one input called message, specifying the data type as string.
131. Now we will code our first node, which is another fundamental element in Langraph.
132. To define a node, we create a standard Python function.
133. Let's create a greeting node function that takes in an input and specifies the output type.
134. The input type of a node needs to be the state, and the output type also has to be the state.
135. The state of our application is the agent state we defined earlier.
136. We will return the updated state after performing actions in this function.
137. It's important to create docstrings for our functions, as they inform AI agents about what the function does.
138. We will write a docstring stating that this is a simple node that adds a greeting message to the state.
139. We will update the state by manipulating the message part of the state.
140. For example, we can concatenate "Hey" with the state message.
141. Finally, we will return the updated state.
142. Now let's build the graph using the state graph framework.
143. To create a graph in Langraph, we use the state graph attribute and pass in our state schema, which is the agent state.
144. We will store this in a variable called graph.
145. To add a node to this graph, we use the inbuilt function graph.add_node, which requires two parameters: the name of the node and the action it will perform.
146. We will name the node "greeter" and specify the action as the greeting node function.
147. Now we need to add the start and end points to the graph.
148. We can do this by calling the inbuilt function set_entry_point and passing the key of the node we want the start node to connect to.
149. We will pass "greeter" as the key for both the start and end points.
150. Finally, we will compile the graph using the inbuilt compile function and store it in a variable.
151. Just because the graph compiles without errors doesn't mean it will run successfully, as there could be logical errors in more complicated graphs.
152. There might be logical errors. Trust me, I know.
153. I want to write some code that will help you visualize this.
154. You can use the IPython library.
155. This code is very similar to the first graph I showed you.
156. The only difference is the name of the node, which we've set to "greater."
157. It is called "greater" because that's the name we gave to this node.
158. Let's run this code.
159. To run it, use the built-in method `invoke`.
160. Let's pass in the message as something like "Bob" and store the result in a variable.
161. To get the value of `result`, we need to reference a certain attribute.
162. The only attribute we have in the entire graph is `message`.
163. We simply put `message`, and we get the final answer, which is "Hey Bob, how's your day going?"
164. This is exactly how we set our function to perform the action.
165. It says "Hey," concatenates the input message (in this case, just the name), and adds "how's your day going?"
166. I could have changed this to anything else; the functions are almost endless.
167. That's the whole flow of how everything works.
168. Hopefully, you understood how to build this very first "Hello World" graph.
169. It's quite simple, but don't worry if you didn't fully understand it.
170. I'm now going to show you the exercise you need to complete to solidify this.
171. The exercise for this graph is quite similar to what we just did.
172. I want you to create a personalized compliment agent.
173. You should pass in your name, like "Bob," and then output something like "Bob, you're doing an amazing job learning Langraph."
174. To give you a hint, you need to concatenate the state, not replace it.
175. This is very similar to what we just did and quite basic.
176. You should be able to do this; it's really just to get your hands dirty.
177. Once you've completed this exercise, join me when we build the second graph.
178. Now we're about to build our second graph.
179. It's again quite similar to the first graph we built, except now we're going to be able to pass multiple inputs.
180. The objectives you will be learning in this are to build a more complicated agent state and create a processing node that performs operations on list data.
181. We will see how to work with different data types apart from just strings.
182. We will set up the entire graph that processes and outputs these results and computes them.
183. The main goal I want you to learn in this subsection is how to handle multiple inputs.
184. Let's code this.
185. I've imported the same things again: the type dictionary and the state graph.
186. I've also imported the list this time.
187. The list is just a simple data structure you should already know.
188. If you remember from the previous graph we made, we are supposed to implement the state schema first.
189. We use the class `AgentState` as a type dictionary.
190. I could have named the state schema anything I wanted; I could have named it something arbitrary like "bottle."
191. In this case, I've just called it `AgentState` because that's how I learned it, and it tells you what it actually is: the state of your agent.
192. The main goal for this graph is to handle and process multiple different inputs.
193. We create multiple keys in the state.
194. Let's say something like `values: List[int]` for a list of integers.
195. Let's also pass in a `name` which will be a string, and have the `result` as a string.
196. Now we are operating on two different types of data structures: a list of integers and a string.
197. We are handling three different inputs: `values`, `name`, and `result`.
198. Let's run this.
199. Now let's build our node.
200. In this graph, we're just going to have a single node to keep things easy.
201. Let's write `def process_values`.
202. We need to pass in the state and return the updated state.
203. We write `state: AgentState` and pass out the `AgentState`.
204. Building healthy habits is important, so let's write a docstring: "This function processes multiple different values and inputs."
205. Now, let's sum the values we pass in and concatenate the name as well, storing it in the result.
206. We pass in `state.result` because the action we're performing is on the `result` attribute.
207. Let's say something like "Hi there" and refer to the `name`.
208. The sum is equal to the built-in Python function `sum(state.values)`.
209. Lastly, we return the updated state.
210. Now we create the graph.
211. This is going to be very similar to what we did in the previous section because there's just a node, a start point, and an endpoint.
212. We use the state graph to initialize a graph and pass in our state schema, `AgentState`, and store this in the variable `graph`.
213. Let's add our node.
214. `graph.add_node` requires two parameters: the name and the action.
215. In this case, the name will be "processor," and the action will be performed by the function `process_values`.
216. Now, I've already told you how to initialize a start point and an endpoint.
217. You attach your entry point to your node, which is the processor node, and the same goes for finish.
218. You compile it using `graph.compile`.
219. Take a moment to think about how this graph will look.
220. It should be very similar to how the graph actually looks, but the only difference is the name of the node, which we've kept as "processor."
221. Now let's test this.
222. We use the `invoke` function.
223. Make sure to store your compiled graph in a variable because if you invoke the graph without compiling it, it won't work.
224. That's why you need to invoke using `app`.
225. If I did `graph.get_graph`, it would say the state graph object has no attribute because your graph hasn't been compiled yet.
226. Let's store this in `answers` and invoke it.
227. Let's pass in some values, like a list of integers: `[1, 2, 3, 4]`, and the name as "Steve."
228. Let's print `answers` to see what happens.
229. You can see your values are `[1, 2, 3, 4]`, your name is "Steve," and your result is "Hi there, Steve. Your sum is equal to 10."
230. This is because that's exactly what we asked the node to perform.
231. If I wanted to access just the result, I could specify `result` and get it in a cleaner manner.
232. Now, I want to try one more thing to build your understanding.
233. Let's add some print statements here.
234. Let's print the state before the action and after the action.
235. This shows how the state gets updated.
236. You can see the values are `[1, 2, 3, 4]`, and the name is "Steve."
237. Notice I didn't pass `result` as an input; Langraph automatically sets that as a `None` value if you don't pass it.
238. If I had used `state.result` to update itself or something else, I would run into a problem because `state.result` has been initialized as `None`.
239. Be mindful of that.
240. In this case, it worked because we're only assigning `state.result`.
241. After the action has been performed, you can see the result is updated.
242. Hopefully, you understood that.
243. It should have been quite intuitive, but to solidify your understanding even more, complete the exercise.
244. I'll see you at the exercise.
245. For your second exercise, I want you to create a graph that passes in a single list of integers along with a name and an operation.
246. If the operation is "plus," you add the elements, and if it's "times," you multiply all the elements, all within the same node.
247. For example, your input could be "Jack Sparrow," your values `[1, 2, 3, 4]`, and your operation "multiplication."
248. Your output should be in the format of "Hi Jack Sparrow, your answer is 24."
249. You would need an if statement in your node, so it's slightly more complicated, but the whole concept is the same.
250. Once you've completed this exercise, I will see you when we build the third graph.
251. Now, welcome to your third graph.
252. This time, we're going to build a sequential graph.
253. This means we're going to create and handle multiple nodes that can sequentially process and update different parts of the state.
254. We will learn how to connect nodes together in a graph through edges.
255. We will invoke the graph and see how the state gets transformed as we progress through our graphs step by step.
256. Your main goal is to understand how to create and handle multiple nodes in Langraph.
257. Let's code this.
258. The imports are the same: state graph and type dictionary.
259. As in the previous two graphs, we will code the state schema or the agent state first.
260. Let's have `class AgentState`.
261. It needs to be in the form of a typed dictionary.
262. Let's have three attributes: `name: str`, `age: str`, and `final: str`.
263. Now, we're about to build our two node functions, which are the actions.
264. Let's name the first one `first_node`.
265. We pass in the state and return the updated state.
266. The docstring will say this is the first node of our sequence.
267. In this node, I want to manipulate the final part.
268. Let's say `state.final = f"{state.name}, hi there."`
269. We return the state.
270. Now we create a new node.
271. Let's call it `second_node`.
272. The docstring will say this is the second node.
273. In this case, I want to have `state.final = f"You are {state.age} years old."`
274. This is a simple example to help you understand.
275. There is one logical error I want you to identify.
276. Once we've built our graph, we would say "Hi" to whoever we pass in, let's say "Charlie."
277. We store that in the final attribute in the state.
278. But when we get to our second node, we replace it with "You are age years old."
279. We want both of them, so we need to concatenate them.
280. We can have `state.final = f"{state.final} {state.age} years old."`
281. Now we have solved the logical error.
282. Let's build the graph.
283. We use `state_graph` to create the graph framework.
284. Let's add these nodes to our graph.
285. We will add the `first_node` and `second_node`.
286. We need to set the entry point and the end point.
287. We connect the first node to the second node using an edge.
288. We use `graph.add_edge` to create a directed edge between the first node and the second node.
289. The flow of data or state updates is from the first node to the second node.
290. Now that we've built that, let's invoke it.
291. Let's pass the parameters as "Charlie" and "20."
292. Print the result.
293. You can see it says "Hi Charlie, you are 20 years old."
294. We could have performed all of this in one single node, but the aim was to create multiple nodes and handle how the state progresses.
295. You learned how to use the `add_edge` method and that you can change the keys of your state at any point in time.
296. Be mindful of replacing content in one of the attributes, as that can lead to logical errors.
297. Now, let's move on to the exercise for this third graph.
298. I want you to build on top of what we just covered.
299. Instead of two nodes, build three nodes in a sequence.
300. You will need to accept the user's name, their age, and a list of their skills.
301. The first node will personalize the name field with a greeting.
302. The second node will describe the user's age.
303. The third node will list all of the user's skills in a formatted string.
304. You will need to combine this and store it in a result field and output that.
305. The format should be something like "Linda, welcome to the system. You are 31 years old, and you have skills in Python, machine learning, and Langraph."
306. You will need to use the `add_edge` method twice.
307. This will solidify your understanding of how to build graphs in general.
308. Once you've done that, answers will be on GitHub for all of the exercises.
309. I will see you in the next section where we build our fourth graph.
310. Welcome! I'm particularly excited to teach you this graph, graph 4.
311. We will learn how to build a conditional graph.
312. For the first time, we will implement conditional logic.
313. We will be using multiple nodes to perform different operations such as addition and subtraction.
314. We will create a router node to handle decisions and control the graph flow.
315. The main goal is to show you how to create conditional edges in Langraph.
316. Let's code this up now.
317. The imports are slightly modified this time.
318. We have the type dictionary and state graph, but now I've also imported start and endpoint.
319. We will design the state schema as `class AgentState`.
320. We will pass in two numbers and an operation, either "plus" or "minus."
321. The final number will be the result of either adding or subtracting the two numbers.
322. Let's create our first node function, `adder`, which adds the two numbers.
323. We will also create a node for subtraction called `subtractor`.
324. Now we will create a node called `decide_next_node`, which will select the next phase of the graph.
325. This node will route the flow based on the operation attribute.
326. If `state.operation` is "plus," we will return the edge for addition.
327. If it's "minus," we will return the edge for subtraction.
328. Now we build the graph using `state_graph`.
329. We will add the nodes to our graph and set the entry and exit points.
330. We will connect the nodes using edges.
331. This will allow us to route the flow of data based on the operation.
332. Once we've built everything, we will invoke it and see how it works.
333. This will help you understand how to implement conditional logic in the overall graph structure.
334. The graph yet will not work due to a subtle reason. The issue lies in the line "Add node router decide next node." The problem is with "decide next node." You can see that the docstring appears once we press "decide next node." The reason this won't work is that in these two functions, we are returning the updated state, but in this node, we are not. We are just returning the edge. This subtle difference is how Langraph works, and you will see why they do it like that shortly.
335. To address this, you can use the code `lambda state`. If you have used lambda functions before, this is easy to understand. If you haven't, don't worry. All this is saying is that your input state will be your output state. In simpler terms, think of this as a pass-through function. Your input state will be passed, and your output will be the exact same state.
336. Why is it the exact same state? Because you're not changing the state at all. You're comparing values, but you're not assigning anything. There's a difference between comparison and assignment. In this case, you're just comparing to see whether the operation is a minus, but no assignment has been made. In fact, there have been no changes to this state whatsoever. That's why we can use this as a pass-through function.
337. Now, let's continue. We will add the edge, which is just the normal edge we did last time. We will need the start key. Here's how you initialize it differently. Remember how we used to do "set entry point" and "set finish point"? We don't do that anymore. We use "start" as the keyword because that's what we imported. Make sure to import it if you do it this way. You use "start" and "end." Your start will be a start point, and you want to connect it to the router.
338. If I put this in quotation marks, that's perfect. Now, why not add node or subtract node? Think back to the diagram. If we connected the start point to the add node or the subtract node, then what's the point of the router in the first place? The whole point was that the router decides what the inputs are and then branches off to the correct node. That's why the router needs to be the first node we connect our start point to.
339. Now we implement the new feature we are going to learn in this section: `graph.add_conditional_edge`. This may look confusing, but it's actually much simpler than it appears. The first part is your source, which is the name of the node. The name of the node we want the conditional edge to be is the router node.
340. Next, it's asking for a path. Before we implement the path, we need to tell it what action it needs to perform. This is where the "decide next node" function comes in. We pass that as the second parameter, which is the path.
341. Now we implement something called the path map, which you should have briefly seen. The path map will be in the form of a dictionary. Earlier, we implemented addition and subtraction operations as edges. Now we're about to create two new edges. Let me write this code for you, and then it will make sense.
342. The code is in the format of edge and node. The starting point of this edge will be the router node, and it's telling us where it will connect to. This visualization will be much easier to understand when I show you the graph. For now, the addition operation and subtraction operation are the edges, and the two nodes are the add node and subtract node.
343. Lastly, we need to create the endpoint. If you look back at the diagram, you can see that we need two edges to connect to the endpoint: one from the add node and one from the subtract node. We can add two edges like this: `graph.edge(start=add_node, end=endpoint)` and `graph.edge(start=subtract_node, end=endpoint)`. Then we compile this with `app = graph.compile`.
344. Now, here comes the most exciting part. Try to visualize what this graph will actually look like. It should look something like this. We have a start point, the router, and our two nodes: add node and subtract node. Notice that the addition operation and subtraction operation are the edge names. It's telling us which direction to go. To go to the add node, we use the addition operation, and to go to the subtract node, we use the subtraction operation.
345. We create these two edges to connect to the endpoint. Let's invoke this graph to see what happens. We define number one as 10, operation as minus, and number two as five. Since we've used subtraction, the final number should be 10 - 5, which is five. We print the results, and the answer is: number one is 10, operation is minus, number two is five, and the final number is five.
346. The way I've invoked it is slightly different from what I have done before. This is another way you can invoke it. Let's go through everything one more time to solidify our understanding.
347. We imported everything. We created the state schema using agent state and a type dictionary. Then we created our three different nodes: the add node, subtract node, and the decide next node. In the decide next node, if the operation is a plus, it goes to the addition operation edge. If it's a subtraction operation, it goes to the subtraction operation edge. This is how we built the graph.
348. We added the nodes, added the edge from the start point to the router, and then added the conditional edge, which we referenced as the router and used the edge node format. The edge will be the addition operation to the add node, and then it will be the subtraction operation to the subtract node.
349. I know this may be confusing at first, but hopefully, the exercise I've given you will help you understand this much better. Now, let's find out what the exercise is for this graph. You need to replicate this structure. At first glance, it looks complex, but if you analyze it closely, all it is is what we just coded twice.
350. You need to input four numbers and two operations and output their final results. For example, number one, number two, number three, number four, and the respective operations and results. In this case, we would have to do 10 - 5, which is 5, and 7 + 2, which is 9. Those two numbers should be outputted.
351. The reason for this exercise is to solidify your understanding of conditional edges, which will be important for the next graphs and AI agents we create. Once you have completed it, cross-reference the answer on GitHub.
352. We are almost at the end of this section and are about to build our final graph, which is graph 5. We have learned a lot about Langraph and its internal mechanisms, which will help us in the next section where we finally build the AI agents.
353. In this subsection, we will learn an important concept: looping. We will create a simple looping graph. The objectives are to implement logic involving looping to route the flow of data back to the nodes and create a single conditional edge, which you know how to do from the previous section.
354. Regarding the previous section, please complete the exercise. It will probably be the hardest exercise you have done until this point. If you didn't get it, look at GitHub to compare where you went wrong. Remember, in Langraph, there is more than one way to build the graphs. Ensure the graphs are well built and function correctly.
355. If you want an extension, try to make it even more robust. Now, let's build the final code for this section. I will show you the graph we want to end up building from the start. The reason for this is to get good practice.
356. Once you finish this course and start making your own AI agent systems, you need to plan how it works. You need to determine what nodes and edges you need, whether it needs to be a conditional edge, and where the start and end points will go. You can do this via pen and paper or software, but you need some sort of blueprint.
357. This is the graph I want to build in this section. There will be a start and end point, and this should be mostly familiar except for the loop. We will create a simple greeting node and another node called the random node. In the greeting node, I want the user to state their name, and it should output "Hi there, your name." The graph will then progress to the random node, where I want to generate five random numbers.
358. Just as a heads up, this graph in the industry would be completely useless, but I've kept it simple so you understand the fundamentals. The loop could have easily been avoided and transferred into a for loop, but this is kept deliberately simple for understanding.
359. Let's start with our agent state. We will create a class for agent state using a type dictionary. For the greeting node, we need a name attribute, and for the random node, we need a list to store the numbers. We also need a counter to know when to stop.
360. When you create your AI agents, you won't know what attributes you need right from the start unless you planned it extremely well. But through practice, you will get better at speculating what attributes you need.
361. Now, let's build these nodes. We start with the greeting node. We define a function for the greeting node, passing in the agent state. We will update the name key to say "Hi there, state.name."
362. We also initialize the counter variable here. This is important because if the user passes in a negative integer, we want to ensure the counter starts at zero. This makes the code more robust.
363. Now, let's create our second node, the random node. This generates a random number from 0 to 10 and appends the randomly generated number to the number list. We also need to increment the counter value.
364. Here's how we implement the looping logic. In any software development program or programming language, there are multiple ways to code an application. The same goes for Langraph. I will show you one way to create a loop.
365. We will create a function called "should_continue" to decide what to do next. If the counter value is less than five, we will return the loop edge and the exit edge.
366. The trajectory should follow this path: we start at the greeting node, then enter the random node, and exit it five times. After five iterations, the if statement will fail, and we will go to the else statement to return exit.
367. Let's quickly make this graph. We initialize the graph and add our two nodes: greeting and random. We create an edge between the greeting and random nodes.
368. Now we create the conditional edges. The source node is random, and the routing function is the "should_continue" function. If the loop is outputted, we go back to the random node; if not, we go to the endpoint.
369. We set the entry point and compile the graph. The graph should match the structure we want. I will put the graph image here for comparison.
370. Now I have this code. I set my name, initialized a new list, and set the counter to -1. The output shows the greeting and the generated random numbers.
371. The counter value is five, and if we had not set it to zero, it would have generated six times. This is how I personally create loops in Langraph. With practice, you may find other ways.
372. This is the final code for our last graph of the section. Please complete the graph 5 exercise.
373. For the exercise, you need to implement an automatic higher or lower game. You need to set the bounds for guessing between 1 to 20 integers, with a maximum of seven guesses. If the guess is correct, it stops; if not, it keeps looping until the limit is reached.
374. The graph should automatically guess without human intervention. Each time a number is guessed, the hint node should say either "higher" or "lower," and the graph should adjust its guesses accordingly.
375. The input should include the player name, an empty list for guesses, attempts set to zero, and bounds of 1 to 20. This allows for easy expansion of the range.
376. Once you complete this exercise, you will reinforce your understanding of loops in Langraph. Cross-reference your answers on GitHub. I will see you in the next section where we finally begin AI agents.
377. Now, let's discuss the `.env` file. If you haven't encountered a `.env` file before, it's essentially a file used to store sensitive information like API keys or configuration values. Its primary purpose is security.
378. I have my own `.env` file stored in my folder structure to keep my API key hidden, as exposing it could lead to financial loss.
379. You might wonder why we need an API key. We require the API key because we are making calls to an external large language model (LLM). If we were using our own LLM, such as through OpenAI, we wouldn't need an API key; we would simply use the OpenAI library integration with LangChain.
380. Since we are using an external service, we need an API to communicate with the LLM hosted on their cloud servers.
381. To load our API key, we can use a simple Python code snippet: `load_dotenv()`.
382. Now that we are on the same page, let's code our AI agent. First, we define the state as we usually do. We will create a class called `AgentState` that is a typed dictionary.
383. The attributes we need in this state are minimal; we really just need one: the messages part.
384. The messages will be in the form of a list of human messages. This is important because when we invoke the graph, we are inputting human messages to inform the LLM that these are messages from the user.
385. We need to specify that these messages are of the type `HumanMessage`.
386. Next, we initialize the large language model (LLM) by writing `lm = ChatOpenAI()`, and we specify the model we want to use. I will be using GPT-4.
387. There are also other models available, such as ChatAnthropic and ChatOpenAI, among others. Personally, I prefer ChatOpenAI because it is straightforward to use.
388. I have also tried using ChatOAI, but I encountered some difficulties integrating it with LangChain, which is why I opted for OpenAI.
389. If you are concerned about costs, don't worry; it is very affordable. You could also consider using the GPT-4 mini model if cost is a significant concern. The input and output tokens are priced in mere pennies for thousands of tokens.
390. Now, let's define our node through a function called `process`, where we will define the state and return it.
391. To call the LLM, LangChain and the LangGraph team use the term "invoke." To run the LLM, we will also use the `invoke` method.
392. We will store the response we get in a variable by calling `lm.invoke()`. This method requires an input of `LanguageModelInput`, which essentially asks what you want the LLM to do.
393. Our question will be contained in the messages, so we will write `state.messages`. When we pass this to the LLM through the invoke method, it will generate a response from its cloud server via our API.
394. The response will then be stored in the `response` variable.
395. We can print this response and return the state.
396. Now, we need to create the graph. We have created a node called `process`, which is where the action occurs, and we have added an edge from the start to the endpoint and compiled the graph.
397. Next, we will ask for user input by writing `user_input = input("Enter something: ")`. We need to invoke the agent since we are creating a graph.
398. Let's run this code now. When we execute `python agentbot.py`, we can enter a message, such as "hi." The AI's response will be "Hello, how can I assist you today?"
399. I assure you that I did not pre-code this response; this is the actual LLM in action. If we run it again and input "Who are you?" it will respond, "I'm an AI language model created by OpenAI called ChatGPT."
400. This confirms that the LLM is functioning correctly. However, why limit ourselves to just one message? We can modify the code to allow for multiple messages, similar to a chatbot.
401. The code for this will involve iterating through user input until the user types "exit," which will break the loop and signify that they no longer wish to interact with the LLM.
402. Let's run this updated code. When we execute `python agentbot.py`, we can say "hi" again, and the AI will respond. We can continue the conversation by asking questions like "Who made you?" or "What is 2 + 2?" and receive appropriate responses.
403. However, if I ask, "What is my name?" the AI will respond, "I'm sorry, but I don't have the ability to know your name or any personal information about you." This is because we have not implemented any memory in the code.
404. This is why I referred to this section as a simple bot. It is not yet an agent; it is merely a basic LLM wrapper.
405. Now you know how to integrate LLMs into your graphs, and it's quite straightforward. The code is only about 25 to 29 lines long.
406. There won't be any exercises for this section since there isn't much to do with this basic implementation.
407. Next, we will build our second AI system, aiming to address the limitations we faced in the previous system, particularly the lack of memory.
408. We will create a chatbot that can remember previous interactions. The objectives for this subsection include using different message types, specifically human and AI messages, and maintaining a full conversation history.
409. We will again use the GPT-4 model with the LangChain's ChatOpenAI library to create a more sophisticated conversation loop.
410. The main goal is to create a form of memory for our agent. Let's begin coding our simple chatbot.
411. As before, I have imported all the necessary libraries, which are largely the same as before, but I have added two new components: the AI message and the Union type annotation.
412. The Union type annotation allows us to define a variable that can hold multiple types of data. If this is your first time encountering it, I recommend reviewing the first chapter for a better understanding.
413. Now, let's define the state again as a class called `AgentState`, which is a typed dictionary.
414. Previously, we defined the state with just a list of human messages. This time, we will also include AI messages to build a more sophisticated chatbot.
415. Instead of creating separate lists for human and AI messages, we can use the Union type annotation to allow for both types in a single list.
416. Human and AI messages are built-in data types within LangGraph and LangChain.
417. While these libraries are great, you can create your own AI agentic system using just Python functions without relying on a library. However, I recommend using these libraries, especially LangGraph, as they provide a good balance of control and simplicity.
418. Now, let's initialize the large language model again, using GPT-4.
419. We will create our node, which will have the same graph structure as before, but the actions we perform will differ slightly.
420. Let's write a docstring for the node, stating that it will solve the request you input.
421. We will invoke the LLM with the state messages, which can be either human or AI messages.
422. We will append the AI message content to the state messages after extracting it from the response.
423. To make the output more readable in the terminal, we will print the state and return it.
424. Now, we will create the same graph structure as before, reusing the code to save time.
425. This time, we will initialize a conversation history to keep track of the dialogue.
426. We will use a while loop to ask the user for their request. The loop will continue until the user types "exit."
427. The conversation history will be updated with the human message, which is the user's input.
428. We will invoke the agent, which is the compiled version of the graph, with the entire conversation history, not just the current human message.
429. This will allow the agent to remember previous interactions, making the conversation more coherent.
430. After processing the input, we will replace the conversation history with the result messages.
431. Let's run the code now. When we execute `python memory_agent.py`, we can test the chatbot's memory.
432. If I say, "Hi, my name is Steve," the AI will respond, "Hi Steve, it's great to meet you. How can I help you today?"
433. If I then ask, "What is my name?" the AI will correctly respond, "You are Steve," demonstrating that it remembers the previous context.
434. We can continue the conversation, and the AI will maintain the context throughout.
435. To visualize the current state, we can add print statements to see how the conversation history evolves.
436. After running the program and inputting various messages, we can observe how the state changes and how the AI responds.
437. However, there are two significant problems with this implementation. The first is that if we exit the program, the conversation history is lost.
438. To address this, we can store the conversation history in a text file. This is a simple solution for prototyping, although a more robust approach would involve using a database.
439. The code for saving the conversation history involves creating a text file and writing each message to it, distinguishing between human and AI messages.
440. After running the program again and inputting messages, we can check the text file to see the logged conversation.
441. The second problem is that as the conversation continues, the length of the state increases, which can lead to higher costs when using the LLM due to the number of tokens consumed.
442. A potential solution is to limit the number of human messages stored in the conversation history. For example, if the number of messages exceeds five, we can remove the oldest message.
443. This approach helps manage costs while still maintaining relevant context in the conversation.
444. We have learned how to integrate human and AI messages into our chatbot and create a more sophisticated system with memory.
445. Now, we will build our third AI agent, which will be a special type known as a React agent, standing for reasoning and acting.
446. This type of agent is common in AI development, and we will learn how to create tools in LangGraph.
447. The objectives for this section include building a React graph, working with different types of messages, and testing the robustness of our graph.
448. The main goal is to create a robust React agent. Let's proceed to the code.
449. This section will be lengthy due to the numerous imports, so I will explain each line to ensure we are all on the same page.
450. The first line imports `Annotated`, `Sequence`, and `TypedDict` from the `typing` module. While we are familiar with `TypedDict`, we have not yet encountered `Annotated` or `Sequence`.
451. `Annotated` is a type annotation that provides additional context to a variable or key without affecting its data type.
452. For example, if we create a `TypedDict` with an email key, we would typically write `email: str`. However, with `Annotated`, we can specify that the email must follow a certain format while still being a string.
453. The email format must be like "abcgmail.com." However, if I pass in "abcd-gmail.com" or something similar, that is not a valid email format anymore, but it is still a string technically. So it would pass through. To resolve this, we use the `annotated` feature.
454. For example, let's say `email` is equal to `annotated`. I won't create the whole type dictionary to save time, but for the example itself, you first pass in the data type you want it to be. We want `email` to be a string, which is not changing.
455. In quotation marks, I provide additional information or context, which adds to the metadata of this key or variable. For instance, I can specify that this has to be a valid email format.
456. To see the metadata, I would write `print(email.metadata)` and then press run. You can see that it states, "this has to be a valid email format," which is the same as what we wrote.
457. Now, let's discuss `sequence`. `Sequence` is also a type annotation that automatically handles state updates for sequences, such as adding new messages to a chat history.
458. This means it helps avoid list manipulation with graph nodes. When using graphs and nodes and updating states, there is a lot of list manipulation involved, which `sequence` helps manage.
459. You don't need to worry about it too much.
460. Next, we have `env` imported from `loadenv`. From last time, we know that this is used to store our API keys, and I've done that here. This will load the API keys.
461. Now, we are importing some new message types: `base message`, `tool message`, and `system message`.
462. Starting with the `tool message`, it is a type of message where the data is passed back to the language model (LM) after the tool has been called. The information passed includes the content itself and the tool call ID.
463. A `system message` is used to provide instructions to the LLM. For example, if you've used LLM APIs before, you might have written, "You are a helpful assistant." That's exactly what a system message is.
464. Don't worry; we will code this up as well, so you'll see what they are.
465. The `base message` is the foundational class for all message types in Langraph. Think of the class hierarchy: the base message is the parent class, and the AI message, human message, tool message, system message, and other message types are the child classes that inherit all the properties of the base message.
466. Each child class, like the tool message, has its own properties, such as content and tool call ID.
467. Now, we have imported `chat` from `openAI`, and we have `state`, `graph`, and `M`, which we are familiar with.
468. We have also imported `tool` and `tool nodes`, which we will cover in the second chapter of this course. These are different elements we will be using in Langraph.
469. The line `from langraph.dosage import add_messages` is a bit different. The `add_messages` function is a reducer function.
470. If this is the first time you're hearing about reducer functions, don't panic; it's not that hard. A reducer function is essentially a rule that controls how updates from nodes are combined with the existing state.
471. In simpler terms, it tells us how to merge new data into the current state. Without a reducer function, updates would completely replace the existing value or state.
472. For example, if I had a state with one attribute, `messages`, set to "hi," and I received an update that says "nice to meet you," without a reducer function, it would overwrite the existing state.
473. In previous graphs and agents we've created, we appended messages, but now that we're using many different messages and tool calls, we can't always append everything; it would become too complicated.
474. That's why we need to leverage a reducer function. If we didn't use a reducer function, it would overwrite the state completely. However, with it, we can append messages, so "hi" becomes "hi nice to meet you."
475. In summary, the reducer function aggregates the data in the state. The reducer function we are discussing is `add_messages`, which allows us to append everything into the state without overwriting it, preserving the state.
476. Now, let's code this react agent.
477. I've cleared the screen, and let's begin with the creation of our state agent.
478. We will only have one key in this example, which is just `messages`.
479. Let's use the new type annotations we've learned: `sequence`, `base message`, and the reducer function `add_messages`.
480. This piece of code indicates that we want to preserve the state by appending it rather than overwriting it, which is what the reducer function does.
481. The sequence of base messages is the data type, and this provides the metadata, which is why we have the `annotated` keyword here.
482. Now, let's create our first tool. Some of you who have come from Langchain might know how to do this already. We use a decorator and define it like this.
483. This decorator tells Python that this function is special because it is a tool we will use. Let's define our tool as `def add(a: int, b: int)`. This function will add two numbers.
484. In the docstring, I will say, "This is an addition function that adds two numbers together."
485. We will return `a + b`, which is simple.
486. Now, how can we infuse these tools into our large language model? First, let's create a list called `tools`.
487. At this moment, I only have one tool, but soon we will have multiple tools, which is why I'm adding this list for now.
488. Let's create our model: `model = chat.openAI`. The model is set to `GPT-4`. I am using GPT-4 because I have never had a problem with it.
489. To tell our GPT-4 large language model that these are the tools it can use, we can use the built-in Python function called `bind_tools`. We pass in the list of tools we have.
490. Now, the large language model will have access to all of our tools.
491. Next, we need to create a node that acts as the agent within our graph. Let's create a simple function called `def model_call(state: agent_state)`. It needs to return the agent state.
492. I will quickly copy this piece of code.
493. This code invokes the model, running it with the system message we are asking. We explicitly tell the large language model that it is our system and to answer our query to the best of its ability.
494. If we want to get technical, we could have written it differently. We could have said `system_prompt`.
495. The system message is this line: "You are my AI system. Please answer my query to the best of your ability."
496. Either way would work, but I think this way is better because it is more readable.
497. This is just another way of writing the updated state. Instead of writing `state['messages'] = something`, we can write it more compactly.
498. We return `messages_response`, updating the messages with the response.
499. The `add_messages` reducer function handles the appending for us, so it doesn't overwrite the state.
500. If I ran this code and built the graph, would it work? No, because when we invoked the model and stored the response, we didn't pass in the query.
501. To add the query, I need to add `state['messages'] = human_message`. The human message will be stored in the messages attribute.
502. Now that we've passed that into our model, we can invoke it, and this should work.
503. Now we define the conditional edge. Why do we need the conditional edge here?
504. The looping part in the graph we created earlier used a conditional edge, and now it will come into play here.
505. Let's define the conditional edge: `def should_continue(state)`. We pass in the state and return `continue`.
506. When I pass in the query and invoke the model, we will create a list of tools. We will get the last message and see if there are any more tools needed to run.
507. If there are, we will go into the continue edge, select the tool, and perform the actions before coming back. If there are no more tool calls left, we will just end the graph.
508. Now, let's define the graph. We initialize the graph through `state_graph` and call the node `R_agent`. The action will be the model call function.
509. We create a tool node, which contains all the different tools. We only have one tool, which is `add`.
510. We set our entry point and point it to `R_agent`. Now, we add our conditional edge.
511. If it goes to the end, we end it. If it goes to tools, we go to the tool node.
512. We also need to add an edge that goes back from our tool to our agent to create a circular connection.
513. The conditional edge provides a one-way directed edge from the agent to the tool node or the endpoint. We need another edge that goes back from the tool node to the agent.
514. Lastly, we compile it with `app = graph.compile()`.
515. I created a new helper function that is not part of Langraph. This code will make the tool calling and everything output in a much better way.
516. Now we can begin. Let's say the input is "add 3 + 4." This line of code streams the data.
517. Let's run this. When we write "add 3 + 4," it calls the tool and knows which tool to pick, returning the result.
518. The tool message shows the result as 7, and the final AI message states, "The sum of three and four is seven."
519. Let's try something more complex: "add 34 + 21." The result is 55, as expected.
520. If I remove the docstring by commenting it out, I will get an error because the function must have a docstring.
521. The docstring is necessary; otherwise, the graph won't work. It tells the LLM what the tool is for.
522. Now, let's try executing both commands: "add 34 + 21" and "add 3 + 4."
523. The results show that the tool was called twice, demonstrating the power of the loop we created.
524. Let's make it even more complicated by adding more tools: `subtract` and `multiply`.
525. We only need to include `subtract` and `multiply` in the tools list.
526. Now, let's run the same command and see if it gets confused with the different tools.
527. The results show that it correctly handles the operations without confusion.
528. Let's try a more complex command: "add 40 + 12 and then multiply the result by 6."
529. The LLM first uses the add tool and then the multiply tool, returning the final answer of 312.
530. Now, let's add a command that doesn't require a tool: "tell me a joke."
531. The LLM handles this gracefully, providing a joke after performing the calculations.
532. This demonstrates the robustness of Langraph; it can handle queries that don't require a tool.
533. After all of this, we now know how to create a react agent.
534. It was a simple react agent, but the concepts remain the same. You can create your own external tools and graphs.
535. That was the goal of this course: to understand how to create these tools and use them.
536. Now, I will see you in the next subsection.
537. We have made great progress so far, so well done.
538. In this next section, we will create a fourth AI agent, and this time we will do things slightly differently.
539. We will be working on a mini project called "Drafter."
540. Picture this: we are working in a company together, and our boss has a problem.
541. The problem is that our company is not working efficiently; we spend too much time drafting documents, and this needs to be fixed.
542. The orders are to create an AI agentic system that can speed up drafting documents and emails.
543. The AI agentic system should allow human-AI collaboration, meaning the human can provide continuous feedback, and the AI agent should stop when the human is satisfied with the draft.
544. The system should also be fast and able to save drafts.
545. We will use Langraph and come up with a sketch for our graph.
546. The sketch will have a start and an endpoint, with our agent having access to tools, including a save tool.
547. The save tool will save the draft, and once it is saved, the process should end.
548. This is different from the react agent, where tools always return to the AI agent.
549. Now, let's code this drafter project together.
550. I have already done all the imports and loaded my environment file.
551. All of these imports are ones you have encountered before, so there is no need to go over them again.
552. The first thing I will do is define a global variable.
553. Defining global variables is a bit odd, but it will become clear as we go through the code.
554. The reason for the global variable is to pass in a state in tools correctly.
555. The proper way to do this in Langraph is through something called injected state, which is beyond the scope of this course.
556. As a workaround, we will use a global variable, and any updates made will update this variable.
557. When we save, the save tool will use the contents of this global variable to save into a text file.
558. Now, let's define our agent state, which is done the same way as last time: `class agent_state(messages: annotated[sequence[base_message]], add_messages: reducer_function)`.
559. We will have two tools: the update tool and the save tool.
560. Let's start with the update tool. I will use the decorator and create `def update(content)`.
561. The content parameter will be provided by the LLM in the background, so you don't need to worry about that.
562. The docstring will state that this updates the document with the provided content.
563. We will interact with the global variable and update the document content with the current content, returning a statement to the LLM that the document has been updated successfully.
564. Now, let's define the save tool. Again, we will use the decorator and request a file name from the LLM.
565. The save tool will handle all the save logic. The docstring will state that it saves the current document to a text file and finishes the process.
566. The arguments will include the file name, which should end with ".txt."
567. If it doesn't, we will append ".txt" to ensure robustness.
568. We will call the global variable again.
569. The next piece of code is not part of Langraph; it simply saves the contents of the global variable under the specified file name.
570. I have also added an exception for debugging purposes to identify any errors.
571. Now, we create a list of tools, which will include the update and save tools.
572. Next, we call the model. Is this it for the model definition? No, we need to bind the tools.
573. Now, we initialize the agent, which will be a node in our graph.
574. The function behind the agent will be defined as `def r_agent(state: agent_state)`.
575. We need to pass in a system message to our LLM.
576. The system prompt will be quite large, so get ready.
577. In this system prompt, I specify that this is a system message and that the content is: "You are Drafter, a helpful writing assistant. You will help the user update and modify documents."
578. I also include instructions on how to use the update and save tools and to always show the current document after modifications.
579. Now, let's add some robustness measures. When we first initialize the agent, we will ensure everything is set up correctly.
580. When writing the first message, we won't directly ask how the user would like to change the document, as we haven't passed in a document yet. If there are no messages in the state, we need to provide an introductory message. We can implement this by checking if the state messages are empty. If they are, we can say, "I'm ready to help you update a document. What would you like to create?" This collects the user input and stores it as a human message in the user message variable.
581. If a message has already been passed in or if we are in the process of updating our draft, we need an else statement that asks, "What would you like to do with the document?" This assumes there is already content in the state messages, prompting the user on how they want to update it further. We also print this under an emoji in the terminal so the user can see what they've inputted, and this is also stored in the user message.
582. Next, we combine all messages, which includes the system prompt, the state messages, and the new user message that we want to update. We then invoke the model using the model invoke function.
583. The code so far is basic; nothing extraordinary has been introduced. The rest of this function includes a print statement for aesthetic purposes in the terminal. The print statements will show the AI response and the tool messages.
584. We also need to return the updated state. Previously, I showed you a concise way to update the states, and from now on, we will update the states in this manner.
585. Now, we create our conditional edge function, which will determine if we should continue or end the conversation. If there are no messages, we will need to continue; it won't go to the end part. This serves as a robustness measure.
586. The code checks the most recent tool message to see if the save tool was used. If the update tool was used, we will continue; if the save tool was used, we will end the program. Thus, to continue, we must use the update tool, and to end, we must use the save tool.
587. We will add print statements to clarify the workflow if needed. Lastly, we need to return continue, as it is checked that the save tool was used. The only other tool left is the update tool, which means we go to the continue edge.
588. Now, we create a function to format print statements in a more readable manner for the terminal. This will be useful when we start invoking the graph and monitoring our process.
589. Next, we initialize the graph through a state graph and add the nodes for the agent and tools. The tools will be a tool node. We will set the entry point at the agent, which is the starting point, and then add an edge between the agent and tools. This directed edge and the conditional edge create the loop for human-AI collaboration.
590. We add the conditional edge, which connects the tools to the continue and end options. Finally, we compile the graph, as we have completed its structure.
591. To run the program, I have written a function to invoke the graph in a compact way. This code will facilitate human-AI collaboration.
592. We used a global variable, which is acceptable. While some may disapprove, it is fine for this beginner-level course. If we wanted to implement more complex features from Langraph, we would need to write the code differently, but for now, we have found a simpler way to perform human-AI collaboration.
593. Let's run the program using the command `python draft.py`. You should see a prompt asking what you would like to add or create in the document. For example, if we want to write an email to our colleague Tom saying we cannot make it to the meeting, we can input, "Write me an email to Tom saying I cannot make it to the meeting." The AI will respond with a draft email.
594. We can provide feedback to improve the email, such as specifying that the meeting was supposed to be at 10:00 a.m. in Canary Wharf. The AI will update the email accordingly.
595. If we want to change the sender's name, we can specify that my name is V, and the AI will update that as well. We can also add that I can meet at 12:00 p.m. in New York the next day.
596. After making all the changes, we can ask the AI to save the document. The AI will use the save tool, and the document will be updated successfully. The current content will be displayed, and the document will be saved with a generated filename.
597. We can also pass in a previous message. The initial empty state was due to passing an empty list, but we could have started with an existing document, allowing the model to know the current content and how to change it.
598. The system is robust; for example, if we run `python drafter.py` and ask it to write an email, it will prompt us for more details, demonstrating its capability to handle incomplete input.
599. The agent node has an LLM in the background, and the bind tools function expands its capabilities by providing tools. However, it doesn't have to use those tools if it doesn't need to.
600. If we want to extend this project, we could add a voice feature using OpenAI Whisper for speech-to-text conversion or Eleven Labs for text-to-speech conversion. We could also implement a GUI and integrate a knowledge base.
601. Now, let's build our fifth AI agent, which will focus on retrieval-augmented generation (RAG). The graph will have a start point and an end point, similar to the previous agent, but with two agents: a retriever agent and the main LLM agent.
602. I will not go into detail about RAG, but I will explain it at a surface level. Let's jump to the code.
603. I have already done the necessary imports, but there are four new imports that we will explain as they come up.
604. We will load our ENV file containing all the API keys and initialize our LLM with a new parameter called temperature. The temperature parameter controls the stochasticity of the model outputs. A temperature of zero makes the outputs more deterministic, while a temperature of one makes them more stochastic.
605. We will create the embedding model, which converts text into vector embeddings. It's crucial that the embedding model is compatible with the LLM being used. For example, using a GBD40 model with an embedding model from a different source may lead to incompatibility due to differences in vector dimensions.
606. We will specify the PDF document containing stock market performance data for 2024. This document has nine pages and includes various details about the stock market.
607. If the PDF is in the wrong directory or cannot be found, an error will be raised for debugging purposes. The PDF loader will load the document, and we will check how many pages it contains.
608. The chunking process will divide the document into manageable pieces. The chunk size is set to 1,000 tokens, and the chunk overlap is set to 200 tokens. This means that consecutive chunks will share some tokens, allowing for better context retention.
609. We will apply the chunking process to all nine pages of the document. The Chroma vector database will store the vector embeddings, and we will specify the file path and collection name for the database.
610. If this is the first time running the command, we will create the collection in the specified directory. A try-except block will handle the creation of the vector embedding database, specifying parameters such as how to split the pages and where to store them.
611. The retriever is a crucial component of RAG, responsible for retrieving the most similar chunks based on a query. We will set the number of chunks returned to five, which is a good middle ground.
612. We will create a tool using the decorator tool, which will take a query as input and return a string. This tool will search and return information from our document.
613. If the query does not find any relevant information, it will return a message indicating that no relevant information was found. If it does find relevant chunks, it will store them in a list and return the results.
614. We will bind the retriever tool to our LLM and create the agent state. The should continue function will check if the last message contains any tool calls to determine whether to proceed or end the conversation.
615. The system prompt will provide detailed instructions to the LLM, ensuring it knows how to respond accurately and minimize hallucinations.
616. We will create a dictionary of our tools and define the underlying function for our LLM agent, which will call the LLM with the current state and return the updated messages.
617. The retriever agent will execute tool calls from the LLM response, checking if the tool name is valid and invoking it if it is. If not, it will prompt the user to retry with a valid tool.
618. We will initialize the graph, adding the two AI agents as nodes and creating the conditional edge. The entry point will be set, and we will compile the graph to store it in the RAG agent.
619. Finally, we will create a function that allows us to ask questions to our graph and receive answers. We can exit the loop by typing "exit" or "quit."
620. Now, let's test the RAG agent by running `python rag_agent.py`. The PDF will load, and we will create the Chroma vector database. We can then ask questions about the document, and the system will retrieve relevant information.
621. For example, if we ask how the S&P 500 performed in 2024, the system will call the retriever tool and return the relevant information, including citations from the document.
622. If we ask about a topic not covered in the document, such as OpenAI's performance in 2024, the system will correctly indicate that there is no relevant information.
623. This demonstrates that our RAG setup is functioning correctly. This concludes the course, and I hope you found it informative. Your journey with Langraph is just beginning, and there are many exciting AI projects you can create.
624. If you have any questions or just want to connect, feel free to reach out on LinkedIn. Thank you for watching, and I hope to see you in another course.