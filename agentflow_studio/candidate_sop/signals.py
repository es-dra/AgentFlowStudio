from __future__ import annotations


HOOK_TERMS = (
    "90%",
    "do not",
    "mistake",
    "wrong",
    "truth",
    "key",
    "secret",
    "must know",
    "why",
    "how",
    "不是",
    "为什么",
    "关键",
    "真相",
    "秘密",
    "一定",
    "必须",
    "别再",
    "不要",
    "竟然",
    "居然",
    "原来",
    "年入",
    "百万",
    "万",
    "消失",
    "五年",
    "重生",
    "末世",
    "广播",
    "天使集团",
    "后悔",
)

CONFLICT_TERMS = (
    "not",
    "but",
    "however",
    "instead",
    "problem",
    "conflict",
    "failure",
    "reversal",
    "不是",
    "但是",
    "却",
    "问题",
    "后悔",
    "消失",
    "失败",
    "冲突",
    "威胁",
    "末世",
    "住嘴",
    "穷酸",
    "受委屈",
    "来晚了",
)

PAYOFF_TERMS = (
    "therefore",
    "solution",
    "method",
    "answer",
    "conclusion",
    "recommend",
    "choose",
    "finally",
    "所以",
    "方法",
    "答案",
    "结果",
    "终于",
    "选择",
    "解决",
    "保护",
    "结束",
    "真相",
    "承认",
    "重生",
    "后悔",
)

SPECIFICITY_TERMS = (
    "年",
    "月",
    "百万",
    "集团",
    "老板",
    "先生",
    "保安",
    "大学",
    "疫苗",
    "广播",
)


def keyword_score(text: str, terms: tuple[str, ...]) -> float:
    normalized = text.lower()
    hits = sum(1 for term in terms if term.lower() in normalized)
    return round(min(hits / 2.0, 1.0), 6)


def specificity_score(text: str) -> float:
    normalized = text.lower()
    hits = sum(1 for term in SPECIFICITY_TERMS if term.lower() in normalized)
    digit_bonus = 1 if any(char.isdigit() for char in text) else 0
    return round(min((hits + digit_bonus) / 3.0, 1.0), 6)
