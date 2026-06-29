from copy import deepcopy
import re
from typing import Any
from xml.etree import ElementTree


SUPPORTED_KINDS = {
    "work-summary",
    "investigation",
    "walkthrough",
    "checklist",
    "dashboard",
}
SUPPORTED_BLOCKS = {
    "markdown",
    "timeline",
    "code-reference",
    "command-output",
    "diff",
    "checklist",
    "metric",
    "table",
    "chart",
    "image",
    "svg",
    "callout",
    "stat-grid",
    "flow",
}
SUPPORTED_CHART_TYPES = {"bar", "line", "donut"}
SUPPORTED_CALLOUT_TONES = {"note", "decision", "warning", "success"}
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SAFE_DATA_IMAGE_PREFIXES = (
    "data:image/png;",
    "data:image/jpeg;",
    "data:image/gif;",
    "data:image/webp;",
    "data:image/svg+xml;",
)
SAFE_SVG_TAGS = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "title",
    "desc",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
}
SAFE_SVG_ATTRS = {
    "aria-label",
    "class",
    "cx",
    "cy",
    "d",
    "fill",
    "height",
    "id",
    "offset",
    "opacity",
    "points",
    "r",
    "role",
    "rx",
    "ry",
    "stroke",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-width",
    "transform",
    "viewBox",
    "width",
    "x",
    "x1",
    "x2",
    "y",
    "y1",
    "y2",
}
BLOCKED_HTML = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
SVG_FORBIDDEN_DECLARATIONS = re.compile(
    r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE
)
SVG_URL_REFERENCE = re.compile(r"url\(\s*(['\"]?)([^'\")]*)\1\s*\)", re.IGNORECASE)


def _is_safe_image_src(src: str) -> bool:
    normalized = src.strip().lower()
    if not normalized:
        return False
    if normalized.startswith(("http://", "https://", "/", "./", "../")):
        return True
    if normalized.startswith(SAFE_DATA_IMAGE_PREFIXES):
        return True
    return False


def _expanded_name(name: str) -> tuple[str | None, str]:
    if name.startswith("{"):
        namespace, _, local = name[1:].partition("}")
        return namespace, local
    return None, name


def _is_safe_svg_element_name(name: str) -> bool:
    namespace, local = _expanded_name(name)
    return namespace in (None, SVG_NAMESPACE) and local in SAFE_SVG_TAGS


def _is_safe_svg_attr_name(name: str) -> bool:
    namespace, local = _expanded_name(name)
    return namespace is None and local in SAFE_SVG_ATTRS


def _is_safe_svg_attr_value(value: str) -> bool:
    normalized = value.strip().lower()
    if any(
        protocol in normalized
        for protocol in (
            "javascript:",
            "vbscript:",
            "data:text/html",
            "http://",
            "https://",
        )
    ):
        return False

    for url_match in SVG_URL_REFERENCE.finditer(value):
        target = url_match.group(2).strip()
        if not target.startswith("#"):
            return False

    return True


def _validate_svg(svg: str) -> None:
    if SVG_FORBIDDEN_DECLARATIONS.search(svg):
        raise ValueError("Unsafe SVG")

    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as error:
        raise ValueError("Unsafe SVG") from error

    root_namespace, root_local = _expanded_name(root.tag)
    if root_namespace not in (None, SVG_NAMESPACE) or root_local != "svg":
        raise ValueError("Unsafe SVG")

    for element in root.iter():
        if not _is_safe_svg_element_name(element.tag):
            raise ValueError("Unsafe SVG")
        for attr, value in element.attrib.items():
            _, attr_name = _expanded_name(attr)
            if attr_name.startswith("on") or not _is_safe_svg_attr_name(attr):
                raise ValueError("Unsafe SVG")
            if isinstance(value, str) and not _is_safe_svg_attr_value(value):
                raise ValueError("Unsafe SVG")


def _validate_visual_block(block: dict[str, Any]) -> None:
    block_type = block.get("type")
    if block_type == "chart" and block.get("chart_type", "bar") not in SUPPORTED_CHART_TYPES:
        raise ValueError("Unsupported chart type")
    if block_type == "image" and not _is_safe_image_src(str(block.get("src", ""))):
        raise ValueError("Unsafe image source")
    if block_type == "svg":
        _validate_svg(str(block.get("svg", "")))
    if block_type == "callout" and block.get("tone", "note") not in SUPPORTED_CALLOUT_TONES:
        raise ValueError("Unsupported callout tone")


def validate_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(raw)

    if payload.get("schema_version") != "0.1":
        raise ValueError("Unsupported schema_version")
    if not payload.get("title"):
        raise ValueError("Artifact title is required")
    if payload.get("kind") not in SUPPORTED_KINDS:
        raise ValueError("Unsupported artifact kind")
    if not isinstance(payload.get("blocks"), list):
        raise ValueError("Artifact blocks must be a list")

    for index, block in enumerate(payload["blocks"]):
        if not isinstance(block, dict):
            raise ValueError(f"Block {index} must be an object")
        block_type = block.get("type")
        if block_type not in SUPPORTED_BLOCKS:
            raise ValueError("Unsupported block type")
        if block_type == "markdown" and BLOCKED_HTML.search(block.get("content", "")):
            raise ValueError("Raw HTML is not allowed")
        _validate_visual_block(block)

    return payload
