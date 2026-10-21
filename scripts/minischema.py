"""Dependency-free validator for the JSON Schema 2020-12 subset used by schema.json.

It exists so validation runs with only the Python standard library. When the
`jsonschema` package is installed, scripts/validate.py also cross-checks with it.
Unsupported keywords are reported as errors instead of being silently ignored.
"""

import re

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description",
    "type", "enum", "const", "properties", "required", "additionalProperties",
    "items", "minItems", "maxItems", "uniqueItems",
    "minLength", "maxLength", "pattern", "minimum",
}

_TYPE_CHECKS = {
    "null": lambda v: v is None,
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _equal(a, b):
    # JSON equality: booleans are not numbers.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def check_schema(schema):
    """Return a list of problems with the schema itself (keywords, $refs, regexes)."""
    problems = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("properties", "$defs"):
                    if not isinstance(value, dict):
                        problems.append(f"{path}/{key}: must be an object")
                        continue
                    for name, sub in value.items():
                        walk(sub, f"{path}/{key}/{name}")
                    continue
                if key not in SUPPORTED_KEYWORDS:
                    problems.append(f"{path}: unsupported keyword '{key}'")
                if key == "$ref":
                    if not (isinstance(value, str) and value.startswith("#/")):
                        problems.append(f"{path}: only local $refs are supported")
                    elif resolve_pointer(schema, value[1:]) is _MISSING:
                        problems.append(f"{path}: unresolvable $ref {value}")
                if key == "pattern":
                    try:
                        re.compile(value)
                    except re.error as exc:
                        problems.append(f"{path}: invalid pattern: {exc}")
                if key == "type":
                    types = value if isinstance(value, list) else [value]
                    for t in types:
                        if t not in _TYPE_CHECKS:
                            problems.append(f"{path}: unknown type {t!r}")
                if key in ("items", "additionalProperties") and isinstance(value, dict):
                    walk(value, f"{path}/{key}")
        else:
            problems.append(f"{path}: schema node must be an object")

    walk(schema, "#")
    return problems


_MISSING = object()


def resolve_pointer(doc, pointer):
    """Resolve an RFC 6901 JSON Pointer. Returns _MISSING when absent."""
    if pointer == "":
        return doc
    if not pointer.startswith("/"):
        return _MISSING
    node = doc
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return _MISSING
            node = node[token]
        elif isinstance(node, list):
            if not token.isdigit() or int(token) >= len(node):
                return _MISSING
            node = node[int(token)]
        else:
            return _MISSING
    return node


def pointer_exists(doc, pointer):
    return resolve_pointer(doc, pointer) is not _MISSING


def validate(instance, schema):
    """Return a list of 'path: message' errors; empty when valid."""
    errors = []
    _validate(instance, schema, schema, "", errors)
    return errors


def _validate(value, node, root, path, errors):
    where = path or "/"
    if "$ref" in node:
        _validate(value, resolve_pointer(root, node["$ref"][1:]), root, path, errors)

    if "type" in node:
        types = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(_TYPE_CHECKS[t](value) for t in types):
            errors.append(f"{where}: expected type {types}, got {type(value).__name__}")
            return

    if "const" in node and not _equal(value, node["const"]):
        errors.append(f"{where}: must equal {node['const']!r}")
    if "enum" in node and not any(_equal(value, option) for option in node["enum"]):
        errors.append(f"{where}: {value!r} is not one of {node['enum']}")

    if isinstance(value, str):
        if "minLength" in node and len(value) < node["minLength"]:
            errors.append(f"{where}: shorter than {node['minLength']}")
        if "maxLength" in node and len(value) > node["maxLength"]:
            errors.append(f"{where}: longer than {node['maxLength']}")
        if "pattern" in node and not re.search(node["pattern"], value):
            errors.append(f"{where}: does not match pattern {node['pattern']}")

    if _TYPE_CHECKS["number"](value) and "minimum" in node and value < node["minimum"]:
        errors.append(f"{where}: below minimum {node['minimum']}")

    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append(f"{where}: fewer than {node['minItems']} items")
        if "maxItems" in node and len(value) > node["maxItems"]:
            errors.append(f"{where}: more than {node['maxItems']} items")
        if node.get("uniqueItems"):
            for i, a in enumerate(value):
                if any(_equal(a, b) for b in value[:i]):
                    errors.append(f"{where}: items are not unique")
                    break
        if "items" in node:
            for i, item in enumerate(value):
                _validate(item, node["items"], root, f"{path}/{i}", errors)

    if isinstance(value, dict):
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing required property '{key}'")
        props = node.get("properties", {})
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], root, f"{path}/{key}", errors)
            elif node.get("additionalProperties") is False:
                errors.append(f"{where}: unexpected property '{key}'")
            elif isinstance(node.get("additionalProperties"), dict):
                _validate(item, node["additionalProperties"], root, f"{path}/{key}", errors)
