import java

from Method caller, Method callee
where caller.calls(callee)
select caller, "calls", callee
