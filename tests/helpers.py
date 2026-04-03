"""
Shared in-memory helpers for deterministic unit and route tests.
"""
from __future__ import annotations

import copy
import re
from types import SimpleNamespace


class CursorStub:
    """List-backed cursor with the small subset of PyMongo methods our tests need."""

    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction=None):
        if isinstance(key, list):
            for field, sort_dir in reversed(key):
                self.docs.sort(
                    key=lambda doc: doc.get(field),
                    reverse=sort_dir == -1,
                )
        else:
            self.docs.sort(
                key=lambda doc: doc.get(key),
                reverse=direction == -1,
            )
        return self

    def limit(self, count):
        return CursorStub(self.docs[:count])

    def __iter__(self):
        return iter(self.docs)

    def __len__(self):
        return len(self.docs)

    def __getitem__(self, item):
        return self.docs[item]


def _matches(document, query):
    if not query:
        return True

    for key, expected in query.items():
        if key == "$or":
            return any(_matches(document, part) for part in expected)
        if key == "$and":
            return all(_matches(document, part) for part in expected)

        value = document.get(key)
        if isinstance(expected, dict):
            regex_value = expected.get("$regex")
            regex_options = expected.get("$options", "")
            if regex_value is not None:
                flags = re.IGNORECASE if "i" in regex_options else 0
                if not re.search(regex_value, str(value or ""), flags):
                    return False

            for operator, operand in expected.items():
                if operator in {"$regex", "$options"}:
                    continue
                if operator == "$ne" and value == operand:
                    return False
                if operator == "$nin" and value in operand:
                    return False
                if operator == "$gt" and not (value is not None and value > operand):
                    return False
                if operator == "$gte" and not (value is not None and value >= operand):
                    return False
                if operator == "$exists" and (key in document) != operand:
                    return False
        elif value != expected:
            return False

    return True


class CollectionStub:
    """Minimal in-memory collection for route/model unit tests."""

    def __init__(self, docs=None):
        self.docs = [copy.deepcopy(doc) for doc in (docs or [])]

    def find(self, query=None, projection=None):
        results = [copy.deepcopy(doc) for doc in self.docs if _matches(doc, query)]
        if projection and projection.get("_id") == 0:
            results = [{k: v for k, v in doc.items() if k != "_id"} for doc in results]
        return CursorStub(results)

    def find_one(self, query=None):
        for doc in self.find(query):
            return doc
        return None

    def insert_one(self, document):
        self.docs.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=document.get("_id", len(self.docs)))

    def update_one(self, query, update):
        for index, doc in enumerate(self.docs):
            if _matches(doc, query):
                updated = copy.deepcopy(doc)
                for field, value in update.get("$set", {}).items():
                    updated[field] = value
                self.docs[index] = updated
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)

    def delete_one(self, query):
        for index, doc in enumerate(self.docs):
            if _matches(doc, query):
                del self.docs[index]
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def distinct(self, field):
        seen = []
        for doc in self.docs:
            value = doc.get(field)
            if value not in seen:
                seen.append(value)
        return seen

    def count_documents(self, query):
        return len(list(self.find(query)))
