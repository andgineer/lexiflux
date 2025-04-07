import logging
import re
from collections.abc import Iterable
from typing import Optional

from lxml import etree

logger = logging.getLogger(__name__)


def clear_html(  # noqa: PLR0915,PLR0912,PLR0913,C901
    input_html: str,
    allowed_tags: Iterable[str] = (
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
    ),
    tags_to_remove_with_content: Iterable[str] = ("script", "style", "head", "iframe", "noscript"),
    keep_empty_tags: Iterable[str] = ("img", "br", "hr", "input"),
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
    # Wrap the input in a wrapper element to ensure we can handle the root element
    input_html = f"<wrapper>{input_html}</wrapper>"

    # Convert iterables to sets for faster lookups
    allowed_tags_set = set(allowed_tags)
    tags_to_remove_set = set(tags_to_remove_with_content)
    keep_empty_tags_set = set(keep_empty_tags)
    ids_to_keep_set = set(ids_to_keep)
    if tags_with_classes is None:
        tags_with_classes = {
            "h1": "display-4 fw-semibold text-primary mb-4",
            "h2": "display-5 fw-semibold text-secondary mb-3",
            "h3": "h3 fw-normal text-dark mb-3",
            "h4": "h4 fw-normal text-dark mb-2",
            "h5": "h5 fw-normal text-dark mb-2",
        }

    # Normalize whitespace: replace newlines and carriage returns with spaces
    input_html = input_html.replace("\n", " ").replace("\r", " ")

    # Parse HTML
    try:
        parser = etree.XMLParser(remove_comments=True, recover=True)
        root = etree.fromstring(input_html, parser=parser)  # noqa: S320
    except Exception:
        logger.exception("Failed to parse HTML, trying to fix malformed HTML")
        return input_html

    # First pass: Remove tags with content
    for tag in tags_to_remove_set:
        for element in root.xpath(f"//{tag}"):
            if element is root:
                continue
            element.getparent().remove(element)

    # Handle unknown tags
    elements_to_unwrap = []
    for element in root.iter():
        if element is root:
            continue

        tag_name = element.tag
        element_id = element.get("id", "")

        # Handle unknown tags - collect for unwrapping
        if tag_name not in allowed_tags_set:
            if element_id and element_id in ids_to_keep_set:
                # Keep the tag if its ID is in ids_to_keep
                pass
            else:
                # Mark for unwrapping (remove tag but keep content)
                elements_to_unwrap.append(element)

    # Unwrap the collected elements - doing this separately avoids modification during iteration
    for element in reversed(elements_to_unwrap):
        parent = element.getparent()
        if parent is None:
            continue

        # Get element's position
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

        # Remove the element now that contents have been preserved
        parent.remove(element)

    # Process remaining elements for class, style, and specified classes
    for element in root.iter():
        if element.tag not in ("html", "body"):
            # Remove class and style attributes if not in tags_with_classes
            if "class" in element.attrib and element.tag not in tags_with_classes:
                del element.attrib["class"]
            if "style" in element.attrib:
                del element.attrib["style"]

            # Add specified classes to tags
            if element.tag in tags_with_classes:
                element.set("class", tags_with_classes[element.tag])

    # Identify empty elements and collapse consecutive br tags
    # We need to do this in multiple passes, as removing elements affects the structure

    def has_meaningful_content(element):
        """Check if element has non-whitespace content or non-empty children."""
        # Check direct text
        if element.text and element.text.strip():
            return True

        # Check children
        for child in element:
            # If child is a preserved empty tag, don't count it as meaningful content
            if child.tag in keep_empty_tags_set:
                continue

            # If child itself has meaningful content, parent has meaningful content
            if has_meaningful_content(child):
                return True

        # Check tail text
        return bool(element.tail and element.tail.strip())

    # Find all br tags in the document for collapsing consecutive brs
    br_xpath = "//br"
    for i in range(3):  # Multiple passes to handle complex nesting
        # First clean empty elements
        elements_to_remove = []
        for element in root.iter():
            # Skip tags that should be kept even if empty
            if element.tag in keep_empty_tags_set:
                continue

            # Skip elements with IDs to keep
            element_id = element.get("id", "")
            if element_id in ids_to_keep_set:
                continue

            # Remove empty elements
            if not has_meaningful_content(element) and element.getparent() is not None:  # noqa: SIM102
                # Don't consider <br> tags alone as meaningful content, but don't remove them either
                if element.tag != "br":
                    tail = element.tail
                    elements_to_remove.append((element, tail))

        # Remove collected empty elements
        for element, tail in elements_to_remove:
            parent = element.getparent()
            if parent is not None:
                if tail:
                    # Preserve tail content
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
        if not elements_to_remove and not br_to_remove:
            break

    # Get the content within our wrapper without the wrapper tags themselves
    result = ""
    # Add the text directly inside the wrapper
    if root.text:
        result += root.text

    # Add HTML for each child element
    for child in root:
        result += etree.tostring(child, encoding="unicode", method="html")

    return re.sub(r"\s+", " ", result).strip()


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
