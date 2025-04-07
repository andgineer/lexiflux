import logging
import re
from collections.abc import Iterable
from typing import Optional

from lxml import etree

TAGS_WITH_CLASSES = {
    "h1": "display-4 fw-semibold text-primary mb-4",
    "h2": "display-5 fw-semibold text-secondary mb-3",
    "h3": "h3 fw-normal text-dark mb-3",
    "h4": "h4 fw-normal text-dark mb-2",
    "h5": "h5 fw-normal text-dark mb-2",
}

KEEP_EMPTY_TAGS = ("img", "br", "hr", "input")

REMOVE_WITH_CONTENT = ("script", "style", "head", "iframe", "noscript")

ALLOWED_TAGS = (
    "p",
    "div",
    "span",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "br",
    "hr",
    "table",
    "tr",
    "td",
    "th",
    "thead",
    "tbody",
    "b",
    "i",
    "strong",
    "em",
    "code",
    "pre",
    "blockquote",
    "sub",
    "small",
)

logger = logging.getLogger(__name__)


def clear_html(  # noqa: PLR0915,PLR0912,PLR0913,C901
    input_html: str,
    allowed_tags: Iterable[str] = ALLOWED_TAGS,
    tags_to_remove_with_content: Iterable[str] = REMOVE_WITH_CONTENT,
    keep_empty_tags: Iterable[str] = KEEP_EMPTY_TAGS,
    ids_to_keep: Iterable[str] = (),
    tags_with_classes: Optional[dict[str, str]] = None,
) -> str:
    """
    Sanitize and normalize HTML content.

    Args:
        input_html: HTML string to clean
        allowed_tags: Tags that are allowed in the output HTML
        tags_to_remove_with_content: Tags to be completely removed along with their content
        keep_empty_tags: Tags that should be kept even if they have no content
        ids_to_keep: IDs that should be kept even if their tags are not in allowed_tags
        tags_with_classes: Dictionary mapping tag names to class strings to add

    Returns:
        Cleaned HTML string
    """
    if not input_html:
        return ""
    input_html = f"<root>{input_html}</root>"

    # Convert to sets for faster lookups
    allowed_tags_set = set(allowed_tags)
    tags_to_remove_set = set(tags_to_remove_with_content)
    keep_empty_tags_set = set(keep_empty_tags)
    ids_to_keep_set = set(ids_to_keep)
    if tags_with_classes is None:
        tags_with_classes = TAGS_WITH_CLASSES

    input_html = input_html.replace("\n", " ").replace("\r", " ")

    try:
        parser = etree.XMLParser(remove_comments=True, recover=True)
        root = etree.fromstring(input_html, parser=parser)  # noqa: S320
    except Exception:
        logger.exception("Failed to parse HTML, trying to fix malformed HTML")
        return input_html

    remove_tags_with_content(root, tags_to_remove_set)
    unwrap_unknow_tags(allowed_tags_set, ids_to_keep_set, root)
    process_class_and_style(root, tags_with_classes)
    remove_empty_elements(ids_to_keep_set, keep_empty_tags_set, root)
    collapse_consecutive_br(root)

    return re.sub(r"\s+", " ", etree_to_str(root)).strip()


def etree_to_str(root):
    result = ""
    if root.text:
        result += root.text
    for child in root:
        result += etree.tostring(child, encoding="unicode", method="html")
    return result


def collapse_consecutive_br(root):  # noqa: C901,PLR0912,PLR0915
    br_xpath = "//br"
    for i in range(3):  # Multiple passes to handle complex nesting
        # Collapse consecutive <br> elements
        br_elements = root.xpath(br_xpath)
        br_to_remove = set()

        i = 0  # noqa PLW2901
        while i < len(br_elements):
            # Skip brs already marked for removal
            if br_elements[i] in br_to_remove:
                i += 1  # noqa PLW2901
                continue

            # Start with current br
            current_br = br_elements[i]
            next_br_idx = i + 1
            consecutive_count = 0

            # Look for consecutive brs
            while next_br_idx < len(br_elements):
                next_br = br_elements[next_br_idx]

                # If already marked for removal, skip
                if next_br in br_to_remove:
                    next_br_idx += 1
                    continue

                # Check if br tags are consecutive
                # (no non-whitespace content between them)
                is_consecutive = False

                # Check if they're direct siblings with only whitespace between
                if current_br.tail is None or current_br.tail.strip() == "":
                    # Check if next element is the next br
                    next_elem = current_br.getnext()
                    while next_elem is not None:
                        if next_elem == next_br:
                            is_consecutive = True
                            break
                        # If there's anything other than whitespace between, not consecutive
                        if next_elem.text and next_elem.text.strip():
                            break
                        if next_elem.tail and next_elem.tail.strip():
                            break
                        next_elem = next_elem.getnext()

                if is_consecutive:
                    # FIXED: Don't remove the next br if it's the last in consecutive sequence
                    consecutive_count += 1
                    if consecutive_count == 1:  # This is the first consecutive br after current
                        # In this case, we want to remove it but preserve any tail
                        tail = next_br.tail
                        br_to_remove.add(next_br)
                        # Preserve tail text for content after the removed br
                        if tail and tail.strip():
                            # Add tail to current br's tail
                            if current_br.tail:
                                current_br.tail += tail
                            else:
                                current_br.tail = tail
                    else:
                        br_to_remove.add(next_br)
                    next_br_idx += 1
                else:
                    break

            # Move to next br not marked for removal
            i = next_br_idx  # noqa PLW2901

        # Remove the brs marked for removal
        for br in br_to_remove:
            parent = br.getparent()
            if parent is not None:
                # Preserve tail content
                if br.tail:
                    prev = br.getprevious()
                    if prev is not None:
                        if prev.tail:
                            prev.tail += br.tail
                        else:
                            prev.tail = br.tail
                    elif parent.text:
                        parent.text += br.tail
                    else:
                        parent.text = br.tail

                parent.remove(br)

        # If no more elements were removed, break the loop
        if not br_to_remove:
            break


def remove_empty_elements(ids_to_keep_set, keep_empty_tags_set, root):  # noqa: PLR0912,C901
    elements_to_remove = []
    for element in root.iter():
        if element.tag in keep_empty_tags_set:
            continue

        element_id = element.get("id", "")
        if element_id in ids_to_keep_set:
            continue

        if (  # noqa: SIM102
            not has_meaningful_content(element, keep_empty_tags_set)
            and element.getparent() is not None
        ):  # noqa: SIM102
            # Don't consider <br> tags alone as meaningful content, but don't remove them either
            if element.tag != "br":
                tail = element.tail
                elements_to_remove.append((element, tail))

    for element, tail in elements_to_remove:
        parent = element.getparent()
        if parent is not None:
            if tail:
                previous = element.getprevious()
                if previous is not None:
                    if previous.tail:
                        previous.tail += tail
                    else:
                        previous.tail = tail
                elif parent.text:
                    parent.text += tail
                else:
                    parent.text = tail

            parent.remove(element)
    return elements_to_remove


def has_meaningful_content(element, keep_empty_tags_set):
    """Check if element has non-whitespace content or non-empty children."""
    if element.text and element.text.strip():
        return True

    for child in element:
        if child.tag in keep_empty_tags_set:
            return True

        if has_meaningful_content(child, keep_empty_tags_set):
            return True

    return bool(element.tail and element.tail.strip())


def process_class_and_style(root, tags_with_classes):
    """Remove class and style attributes from elements not in tags_with_classes."""
    for element in root.iter():
        if element.tag not in ("html", "body"):
            if "class" in element.attrib and element.tag not in tags_with_classes:
                del element.attrib["class"]
            if "style" in element.attrib:
                del element.attrib["style"]

            if element.tag in tags_with_classes:
                element.set("class", tags_with_classes[element.tag])


def unwrap_unknow_tags(allowed_tags_set, ids_to_keep_set, root):  # noqa: C901,PLR0912
    elements_to_unwrap = []
    for element in root.iter():
        if element is root:
            continue

        tag_name = element.tag
        element_id = element.get("id", "")

        if tag_name not in allowed_tags_set and (
            not element_id or element_id not in ids_to_keep_set
        ):
            elements_to_unwrap.append(element)

    for element in reversed(elements_to_unwrap):
        parent = element.getparent()
        if parent is None:
            continue

        pos = parent.index(element)

        # Handle text content
        if element.text:
            if pos > 0:
                # Add to tail of previous sibling
                prev = parent[pos - 1]
                if prev.tail:
                    prev.tail += element.text
                else:
                    prev.tail = element.text
            # Add to parent's text
            elif parent.text:
                parent.text += element.text
            else:
                parent.text = element.text

        # Move each child to parent
        children = list(element)
        for i, child in enumerate(children):
            parent.insert(pos + i, child)

        # Handle tail text
        if element.tail:
            if len(children) > 0:
                # Add to tail of last child
                if children[-1].tail:
                    children[-1].tail += element.tail
                else:
                    children[-1].tail = element.tail
            elif pos > 0:
                # Add to tail of previous sibling
                prev = parent[pos - 1]
                if prev.tail:
                    prev.tail += element.tail
                else:
                    prev.tail = element.tail
            # Add to parent's text
            elif parent.text:
                parent.text += element.tail
            else:
                parent.text = element.tail

        parent.remove(element)


def remove_tags_with_content(root, tags_to_remove_set):
    for tag in tags_to_remove_set:
        for element in root.xpath(f"//{tag}"):
            if element is not root:
                element.getparent().remove(element)


# Example usage
if __name__ == "__main__":
    input_html = "<div>Line 1<br>  \n  <br>Line 2</div>"
    expected_output = "some headerin header"
    result = clear_html(input_html)
    print(result)

    # Test case 1: Consecutive <br> tags
    test1 = "<html><head><title>Title</title></head><body><p>Hello<br><br>World</p></body></html>"
    print(clear_html(test1))

    # Test case 2: Remove style and add class
    test2 = '<div><style>h1 { color: red; }</style><h1 class="red">Heading</h1></div>'
    print(clear_html(test2, tags_with_classes={"h1": "title-class"}))

    # Test case 3: Custom tags
    test3 = "<section><p>text</p><custom>more text</custom></section>"
    print(clear_html(test3))
