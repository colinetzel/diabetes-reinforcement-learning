# diabetes-reinforcement-learning #
Artificial pancreas reinforcement learning project group for CS 980: Topics/Machine Learning

# Goal #
Learn an effective RL algorithm to keep glucose in the tolerable region while avoiding severe hypoglycemia. Algorithm also needs to learn how to avoid hyperglycemia in the long run.

# Exploratory phase #
try several different non-RL heuristic algorithms and learn a RL algorithm from the data
Starts with a simple random non-RL heuristic, PID and PID with insulin feedback also implemented

# Learning phase #
Calculate value functions / q-functions, learn algorithm (with td or another RL method)
Assumption is heuristics are safe policies, goal is to ensure safety is maintained during the learning step (a safe policy is not necessarily guaranteed even if the heuristics are all safe individually!)

Unrestricted reinforcement learning (random exploration of states, no measures to ensure patient safety during process) to be used as a benchmark as an ideal output policy to compare to

# Outcome #
Mostly unsuccessful, the algorithms can cope with slow basal glucose production by liver but cannot keep insulin in tolerable region with carbohydrate spikes from meals. Failure to avoid post-prandrial hypoglycemia is seen in this simulator and in outside research on pure PID algorithms.

The failure for insulin feedback is likely that the simulator's insulin model is different from the one used in the paper the model was taken from. Glucosym's insulin estimates do not correlate well with the insulin estimates made by said model.


# References #
Insulin feedback model was taken from:
Effect of Insulin Feedback on Closed-Loop Glucose Control: A Crossover Study by Ruiz et al.
https://www.ncbi.nlm.nih.gov/pubmed/23063039

The simulator used is glucosym, located at: https://github.com/Perceptus/GlucoSym
