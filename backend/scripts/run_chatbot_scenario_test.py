import functools
from typing import Callable, List, Dict, Any

def make_test_interceptor(
    original_func: Callable[..., Any], captured_list: List[Dict[str, Any]]
) -> Callable[..., Any]:
    @functools.wraps(original_func)
    def wrapper(auth_header: str, message: str, **kwargs: Any) -> Any:
        captured_list.append(kwargs)
        return original_func(auth_header, message, **kwargs)
    return wrapper

def evaluate_scenario(captured: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """기대값(expected)의 인자들이 캡처된 인자(captured)에 부분 집합으로 모두 포함되어 있는지 검사합니다(Subset Match)."""
    tool_match = captured.get("tool_name") == expected.get("tool_name")
    
    cap_args = captured.get("arguments") or {}
    exp_args = expected.get("arguments") or {}
    args_match = True
    for k, v in exp_args.items():
        if cap_args.get(k) != v:
            args_match = False
            break
            
    status = "PASS" if (tool_match and args_match) else "FAIL"
    return {
        "status": status,
        "tool_match": tool_match,
        "args_match": args_match
    }
