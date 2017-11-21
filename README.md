# diabetes-reinforcement-learning #
Artificial pancreas reinforcement learning project group for CS 980: Topics/Machine Learning

# Goal #
Learn an effective RL algorithm to keep glucose in the tolerable region while avoiding severe hypoglycemia. Algorithm also needs to learn how to avoid hyperglycemia in the long run.

# Exploratory phase #
try several different non-RL heuristic algorithms and learn a RL algorithm from the data
Start with three or four heuristic methods

# Learning phase #
Calculate value functions / q-functions, learn algorithm (with td or another RL method)
Assumption is heuristics are safe policies, goal is to ensure safety is maintained during the learning step (a safe policy is not necessarily guaranteed even if the heuristics are all safe individually!)

Unrestricted reinforcement learning (random exploration of states, no measures to ensure patient safety during process) to be used as a benchmark as an ideal output policy to compare to
