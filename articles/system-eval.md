Evaluation pipelines run models against test sets and score the results, often using another model as an automated judge or grader. They require sound [evaluation data and benchmark governance](../nodes/life-evaluate.md), because the judge prompts, test sets, and grading code are themselves dependencies whose integrity determines whether reported results mean anything.

## Trust boundary

An evaluation harness sits at the point where a system decides "is this output acceptable." If that decision can be influenced, the pipeline becomes a target rather than a neutral measurement. The component is relevant to automated judge or grader manipulation, where content under test steers the grader toward a favorable verdict, and to benchmark or evaluation contamination, where test material leaks into training or is otherwise gamed so that scores no longer reflect capability. Because judges are frequently the same class of model being evaluated, they can inherit the same susceptibilities.

For standardized red-teaming and agent-evaluation environments, consult the cited sources.
