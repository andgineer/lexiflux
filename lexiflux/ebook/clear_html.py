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

    try:
        root = parse_partial_html(input_html)
    except Exception:
        logger.exception("Failed to parse HTML, returning original")
        return input_html

    # Convert to sets for faster lookups
    allowed_tags_set = set(allowed_tags)
    tags_to_remove_set = set(tags_to_remove_with_content)
    keep_empty_tags_set = set(keep_empty_tags)
    ids_to_keep_set = set(ids_to_keep)
    if tags_with_classes is None:
        tags_with_classes = TAGS_WITH_CLASSES

    remove_tags_with_content(root, tags_to_remove_set)
    unwrap_unknow_tags(allowed_tags_set, ids_to_keep_set, root)
    process_class_and_style(root, tags_with_classes)
    remove_empty_elements(ids_to_keep_set, keep_empty_tags_set, root)
    collapse_consecutive_br(root)

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

    parser = etree.HTMLParser(remove_comments=True)
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


def collapse_consecutive_br(root):  # noqa: C901,PLR0912,PLR0915
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
                {"img", "br", "hr", "input"},
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


def is_empty_div_with_only_br(element, keep_empty_tags_set):
    """Check if an element is a div that contains only <br> tags and whitespace.

    Args:
        element: The element to check
        keep_empty_tags_set: Set of tags that should be kept even when empty

    Returns:
        True if the element is a div with only <br> tags and whitespace, False otherwise
    """
    if element.tag != "div":
        return False

    # Check if element has text content before any children
    if element.text and element.text.strip():
        return False

    # Check all children
    for child in element:  # noqa: SIM102
        # If child is not a <br>, and it's not an empty element that should be kept anyway
        if child.tag != "br" and child.tag not in keep_empty_tags_set:  # noqa: SIM102
            # Check if the child has meaningful content
            if has_meaningful_content(child, keep_empty_tags_set):
                return False

        # Check tail text of child - THIS IS THE FIX
        # If there's any non-whitespace text after a <br> tag, don't consider it empty
        if child.tail and child.tail.strip():
            return False

    # If we got here, the div only has <br> tags and/or whitespace
    return True


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

            # Check if it's a div with only <br> tags
            if is_empty_div_with_only_br(element, keep_empty_tags_set):
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
                not has_meaningful_content(element, keep_empty_tags_set)
                and element.getparent() is not None
            ):
                # Don't consider <br> tags alone as meaningful content
                if element.tag != "br":
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


def has_meaningful_content(element, keep_empty_tags_set):
    """Check if element has non-whitespace content or non-empty children."""
    # First, directly check if this element should be kept regardless
    if element.tag in keep_empty_tags_set:
        return True

    # Then check for text content
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
