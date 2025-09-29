/**
 * @name Fan-in and Fan-out for Python
 * @description Calculates the Fan-in and Fan-out for each function and method.
 * @kind table
 */
import python

from Callable c
where
  // Exclude trivial built-in functions and focus on code from the repository
  c.getModule().isUserCode() and
  not c.isLambda()
select
  c.getQualifiedName() as functionName,
  count(distinct c.getACall().getCallee()) as fan_out,
  count(distinct c.getACaller()) as fan_in
