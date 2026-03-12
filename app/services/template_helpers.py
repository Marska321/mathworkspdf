from __future__ import annotations

import math
from typing import Any


PLACE_TO_INDEX = {
    "ones": 0,
    "tens": 1,
    "hundreds": 2,
    "thousands": 3,
}


def get_digit_at_place(number: int, place: str) -> int:
    return int(str(number).zfill(PLACE_TO_INDEX[place] + 1)[-(PLACE_TO_INDEX[place] + 1)])


def get_place_multiplier(place: str) -> int:
    return 10 ** PLACE_TO_INDEX[place]


def mark_digit(number: int, place: str) -> str:
    digits = list(str(number))
    index = len(digits) - PLACE_TO_INDEX[place] - 1
    digits[index] = f"<u>{digits[index]}</u>"
    return "".join(digits)


def expand_number(number: int) -> list[int]:
    digits = [int(digit) for digit in str(number)]
    powers = list(range(len(digits) - 1, -1, -1))
    return [digit * (10 ** power) for digit, power in zip(digits, powers) if digit]


def expand_number_as_text(number: int) -> str:
    return " + ".join(str(value) for value in expand_number(number))


def round_down_to_place(number: int, place: str) -> int:
    multiplier = get_place_multiplier(place)
    return (number // multiplier) * multiplier


def round_up_to_place(number: int, place: str) -> int:
    multiplier = get_place_multiplier(place)
    return ((number + multiplier - 1) // multiplier) * multiplier


def round_to_place_value(number: int, place: str) -> int:
    multiplier = get_place_multiplier(place)
    half_step = multiplier // 2
    return ((number + half_step) // multiplier) * multiplier


def no_regroup(a: int, b: int) -> bool:
    return all(((a // (10 ** place)) % 10) + ((b // (10 ** place)) % 10) < 10 for place in range(max(len(str(a)), len(str(b)))))


def requires_regroup(a: int, b: int) -> bool:
    return not no_regroup(a, b)


def no_regroup_subtraction(a: int, b: int) -> bool:
    return all(((a // (10 ** place)) % 10) >= ((b // (10 ** place)) % 10) for place in range(max(len(str(a)), len(str(b)))))


def requires_regroup_subtraction(a: int, b: int) -> bool:
    return not no_regroup_subtraction(a, b)


def compare_symbol(a: int, b: int) -> str:
    if a < b:
        return "<"
    if a > b:
        return ">"
    return "="


def sort_ascending(numbers: list[int]) -> list[int]:
    return sorted(numbers)


def sort_descending(numbers: list[int]) -> list[int]:
    return sorted(numbers, reverse=True)


def distractor_ignore_carry(a: int, b: int) -> int:
    ones = ((a % 10) + (b % 10)) % 10
    tens = (a // 10) + (b // 10)
    return tens * 10 + ones


def distractor_borrow_not_applied(a: int, b: int) -> int:
    return ((a // 10) - (b // 10)) * 10 + abs((a % 10) - (b % 10))


def digit_only(value: int) -> int:
    return int(str(value)[0]) if value >= 10 else value


def adjacent_place_value(value: int) -> int:
    return value * 10 if value < 1000 else max(1, value // 10)


def shade_indices(numerator: int, denominator: int) -> list[int]:
    return list(range(min(numerator, denominator)))


def to_mixed_number(numerator: int, denominator: int) -> str:
    whole = numerator // denominator
    remainder = numerator % denominator
    if remainder == 0:
        return str(whole)
    if whole == 0:
        return f"{remainder}/{denominator}"
    return f"{whole} {remainder}/{denominator}"


def all_unique(values: list[Any]) -> bool:
    return len(values) == len(set(values))


def apply_rule(value: int, operation: str, operand: int) -> int:
    if operation == "add":
        return value + operand
    if operation == "subtract":
        return value - operand
    if operation == "multiply":
        return value * operand
    raise ValueError(f"Unsupported operation: {operation}")


def flow_rule_text(operation: str, operand: int) -> str:
    if operation == "add":
        return f"+ {operand}"
    if operation == "subtract":
        return f"- {operand}"
    if operation == "multiply":
        return f"x {operand}"
    raise ValueError(f"Unsupported operation: {operation}")


def format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def join_csv(values: list[Any]) -> str:
    return ", ".join(str(value) for value in values)


HELPER_REGISTRY = {
    "abs": abs,
    "adjacent_place_value": adjacent_place_value,
    "all_unique": all_unique,
    "apply_rule": apply_rule,
    "ceil": math.ceil,
    "compare_symbol": compare_symbol,
    "digit_only": digit_only,
    "distractor_borrow_not_applied": distractor_borrow_not_applied,
    "distractor_ignore_carry": distractor_ignore_carry,
    "expand_number": expand_number,
    "expand_number_as_text": expand_number_as_text,
    "flow_rule_text": flow_rule_text,
    "format_time": format_time,
    "get_digit_at_place": get_digit_at_place,
    "get_place_multiplier": get_place_multiplier,
    "join_csv": join_csv,
    "len": len,
    "mark_digit": mark_digit,
    "math_gcd": math.gcd,
    "max": max,
    "min": min,
    "no_regroup": no_regroup,
    "no_regroup_subtraction": no_regroup_subtraction,
    "requires_regroup": requires_regroup,
    "requires_regroup_subtraction": requires_regroup_subtraction,
    "round": round,
    "round_down_to_place": round_down_to_place,
    "round_to_place_value": round_to_place_value,
    "round_up_to_place": round_up_to_place,
    "set": set,
    "shade_indices": shade_indices,
    "sort_ascending": sort_ascending,
    "sort_descending": sort_descending,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "to_mixed_number": to_mixed_number,
}
