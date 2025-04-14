import logging
import re
from collections.abc import Iterable
from typing import Optional

from lxml import etree
from lxml.html import fragments_fromstring, tostring

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

CDATA_START = "<![CDATA["
CDATA_END = "]]>"

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

    # Normalize new lines to spaces for consistent handling
    input_html = re.sub(r"[\n\r]+", " ", input_html)
    input_html = re.sub(r"<!\[CDATA\[.*?]]>", "", input_html, flags=re.DOTALL)

    try:
        root = parse_partial_html(input_html)
    except Exception:
        logger.exception("Failed to parse HTML, returning original")
        return input_html

    # Convert to sets for faster lookups
    tags_to_remove_set = set(tags_to_remove_with_content)
    keep_empty_tags_set = set(keep_empty_tags)
    allowed_tags_set = set(allowed_tags) | set(keep_empty_tags)
    ids_to_keep_set = set(ids_to_keep)
    if tags_with_classes is None:
        tags_with_classes = TAGS_WITH_CLASSES

    remove_tags_with_content(root, tags_to_remove_set)
    unwrap_unknow_tags(allowed_tags_set, ids_to_keep_set, root)
    process_class_and_style(root, tags_with_classes)
    remove_empty_elements(ids_to_keep_set, keep_empty_tags_set, root)
    collapse_consecutive_br(root, keep_empty_tags_set)

    return re.sub(r"\s+", " ", etree_to_str(root)).strip()


def parse_partial_html(input_html):
    """Parse string with HTML fragment into an lxml tree.

    Supports partial HTML content.
    Removes comments.
    """
    # Simple heuristic to detect unclosed comments
    open_count = input_html.count("<!--")
    close_count = input_html.count("-->")

    # If counts don't match, escape all opening comment tags
    if open_count != close_count:
        input_html = input_html.replace("<!--", "&lt;!--")

    parser = etree.HTMLParser(recover=True, remove_comments=True, remove_pis=True)
    fragments = fragments_fromstring(input_html, parser=parser)
    root = etree.Element("root")
    for fragment in fragments:
        if isinstance(fragment, str):
            if root.text is None:
                root.text = fragment
            else:
                root.text += fragment
        else:
            root.append(fragment)
    return root


def etree_to_str(root):
    result = ""
    if root.text:
        result += root.text
    for child in root:
        result += tostring(child, encoding="unicode", method="html")
    return result


def collapse_consecutive_br(root, keep_empty_tags_set):  # noqa: C901,PLR0912,PLR0915
    """From <br> tags sequence, keep only the first one.

    This function searches for consecutive <br> tags and removes all but the first one
    in each sequence. Whitespace between <br> tags is ignored for determining consecutive tags.

    Args:
        root: The root element of the lxml tree
    """
    # Process each element in the tree
    for element in root.iter():
        # Skip the root element itself
        if element is root:
            continue

        # Get all children as a list
        children = list(element)
        if not children:
            continue

        # We'll track if we've seen a <br> and which one it was
        last_br = None
        br_tags_to_remove = []

        # Check each child
        for child in children:
            if child.tag == "br":
                if last_br is not None and (not last_br.tail or not last_br.tail.strip()):
                    # This is a consecutive <br>, mark it for removal
                    br_tags_to_remove.append(child)
                else:
                    # This is the first <br> in a potential sequence
                    last_br = child
            # This is not a <br> tag
            # If the child has meaningful text content, reset last_br
            elif (child.text and child.text.strip()) or has_meaningful_content(
                child,
                keep_empty_tags_set,
            ):
                last_br = None

        # Remove consecutive <br> tags and preserve their tail text
        for br_tag in br_tags_to_remove:
            if br_tag.tail:
                # There's text after this <br> that needs to be preserved
                # Add it to the tail of the first <br> or another previous sibling
                if last_br is not None:
                    if last_br.tail:
                        last_br.tail += br_tag.tail
                    else:
                        last_br.tail = br_tag.tail
                # If no first <br> (shouldn't happen), add to parent's text
                elif element.text:
                    element.text += br_tag.tail
                else:
                    element.text = br_tag.tail

            # Now remove the br tag
            parent = br_tag.getparent()
            if parent is not None:
                parent.remove(br_tag)


def remove_cdata(element):
    if element.text and CDATA_START in element.text:
        start_idx = element.text.find(CDATA_START)
        end_idx = element.text.find(CDATA_END, start_idx)
        if end_idx != -1:
            element.text = element.text[:start_idx] + element.text[end_idx + len(CDATA_END) :]


def remove_empty_elements(ids_to_keep_set, keep_empty_tags_set, root):  # noqa: PLR0912,C901,PLR0915
    """Remove empty elements and divs that contain only <br> tags and whitespace.

    Args:
        ids_to_keep_set: Set of element IDs that should be preserved
        keep_empty_tags_set: Set of tags that should be kept even when empty
        root: The root element of the lxml tree

    Returns:
        List of removed elements
    """
    # We'll iterate until no more elements are removed
    elements_removed = True
    elements_to_remove = []

    while elements_removed:
        elements_removed = False
        elements_to_remove = []

        for element in root.iter():
            if element is root:
                continue

            element_id = element.get("id", "")
            if element_id in ids_to_keep_set:
                continue

            # Skip elements that should be kept even when empty
            if element.tag in keep_empty_tags_set:
                continue

            if not has_meaningful_content(element, keep_empty_tags_set - {"br"}):
                # Get the parent and prepare to remove this element
                parent = element.getparent()
                if parent is not None:
                    # Preserve any tail text
                    tail = element.tail
                    elements_to_remove.append((element, tail))
                    elements_removed = True
                    continue

            # Check if element is completely empty
            if (  # noqa: SIM102
                not has_meaningful_content(element, keep_empty_tags_set, check_tail=False)
                and element.getparent() is not None
            ):
                tail = element.tail
                elements_to_remove.append((element, tail))
                elements_removed = True

        # Remove elements identified in this iteration
        for element, tail in elements_to_remove:
            parent = element.getparent()
            if parent is not None:
                # Preserve tail text by adding it to previous sibling or parent
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

                # We need to preserve the content of any children before removing
                # This is a major fix - we need to preserve all text from children
                for child in element:
                    # If the child has tail text, we need to preserve it
                    if child.tail and child.tail.strip():
                        # Add to parent's text or previous sibling's tail
                        previous = element.getprevious()
                        if previous is not None:
                            if previous.tail:
                                previous.tail += child.tail
                            else:
                                previous.tail = child.tail
                        elif parent.text:
                            parent.text += child.tail
                        else:
                            parent.text = child.tail

                # Remove the element
                parent.remove(element)

        # If we removed elements, we need to check again
        if elements_removed:
            continue

    return elements_to_remove


def has_meaningful_content(element, keep_empty_tags_set, check_tail=True):
    """Check if element/children has non-whitespace content or in the `keep_empty_tags_set`."""
    if element.tag in keep_empty_tags_set:
        return True

    if element.text and element.text.strip():
        return True

    if check_tail and element.tail and element.tail.strip():
        return True

    return any(has_meaningful_content(child, keep_empty_tags_set) for child in element)


def process_class_and_style(root, tags_with_classes):
    """Remove class and style attributes from elements not in tags_with_classes."""
    for element in root.iter():
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
        remove_cdata(element)

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
    """Remove specified tags along with their content."""
    for tag in tags_to_remove_set:
        for element in root.xpath(f"//{tag}"):
            if element is not root:
                parent = element.getparent()
                if parent is not None:
                    # Preserve tail text if present
                    if element.tail and element.tail.strip():
                        prev = element.getprevious()
                        if prev is not None:
                            if prev.tail:
                                prev.tail += element.tail
                            else:
                                prev.tail = element.tail
                        elif parent.text:
                            parent.text += element.tail
                        else:
                            parent.text = element.tail

                    # Remove the element
                    parent.remove(element)


# Example usage
if __name__ == "__main__":
    input_html = "<![CDATA[This is CDATA content with <tags> that shouldn't be parsed]]>"
    result = clear_html(input_html)
    print(f"result=`{result}`")
