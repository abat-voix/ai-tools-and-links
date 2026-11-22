import argparse
import json
import math
from pathlib import Path


def normalize(vector: list[float]) -> list[float]:
    """Вернуть единичный вектор или отклонить некорректный вход."""
    if not vector or not all(math.isfinite(value) for value in vector):
        raise ValueError("Вектор должен содержать конечные числа")
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0 or not math.isfinite(length):
        raise ValueError("Длина вектора должна быть конечной и больше нуля")
    return [value / length for value in vector]


def dot(left: list[float], right: list[float]) -> float:
    """Вычислить скалярное произведение векторов одной размерности."""
    if len(left) != len(right) or not left:
        raise ValueError("Нужны непустые векторы одной размерности")
    if not all(math.isfinite(value) for value in left + right):
        raise ValueError("Векторы должны содержать конечные числа")
    return sum(a * b for a, b in zip(left, right, strict=True))


def rank(
    query: list[float],
    documents: list[dict],
    threshold: float = 0.8,
) -> list[dict]:
    """Ранжировать документы по косинусу и оставить прошедшие порог."""
    if not math.isfinite(threshold) or not -1 <= threshold <= 1:
        raise ValueError("Порог должен быть в диапазоне [-1, 1]")
    unit_query = normalize(query)
    matches = []
    for document in documents:
        score = dot(unit_query, normalize(document["vector"]))
        if score >= threshold:
            matches.append({"id": document["id"], "score": score})
    return sorted(matches, key=lambda item: (-item["score"], item["id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Поиск на синтетических векторах")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    source = Path(__file__).with_name("vectors.json")
    fixture = json.loads(source.read_text(encoding="utf-8"))
    for query in fixture["queries"]:
        print(json.dumps({
            "query": query["id"],
            "threshold": args.threshold,
            "matches": rank(query["vector"], fixture["documents"], args.threshold),
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
