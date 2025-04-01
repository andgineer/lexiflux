import logging
from collections.abc import Iterable

from bs4 import BeautifulSoup, Comment, Tag

log = logging.getLogger(__name__)


def clear_html(
    input_html: str,
    allowed_tags: Iterable[str] = (
        "p",
        "div",
        "span",
        "br",
        "hr",
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
        "blockquote",
        "strong",
        "em",
        "b",
        "i",
        "small",
        "sub",
        "sup",
        "pre",
        "code",
        "table",
        "tr",
        "td",
        "th",
        "thead",
        "tbody",
    ),
    tags_to_remove_with_content: Iterable[str] = (
        "head",
        "style",
        "script",
        "svg",
        "noscript",
        "form",
        "input",
        "option",
        "select",
        "textarea",
    ),
    tags_with_classes: dict[str, str] | None = None,
) -> str:
    """Clean HTML by keeping only whitelisted tags and removing class/style attributes.

    Args:
        input_html: The HTML string to clean
        allowed_tags: Whitelist of tags that should be kept
        tags_to_remove_with_content: Tags that should be removed along with their content
        tags_with_classes: Dict mapping tags to classes to add

    Returns:
        Cleaned HTML string with only allowed tags and without class/style attributes
    """
    if not input_html:
        return ""

    if tags_with_classes is None:
        tags_with_classes = {
            "h1": "display-4 fw-semibold text-primary mb-4",
            "h2": "display-5 fw-semibold text-secondary mb-3",
            "h3": "h3 fw-normal text-dark mb-3",
            "h4": "h4 fw-normal text-dark mb-2",
            "h5": "h5 fw-normal text-dark mb-2",
        }

    try:
        soup = BeautifulSoup(input_html, "html.parser")

        # Step 1: Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Step 2: Remove tags with their content
        for tag_name in tags_to_remove_with_content:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Step 3: Process remaining tags
        process_tags(soup, allowed_tags)

        # Step 4: Remove empty p tags
        remove_empty_tags(soup, "p")

        # Step 5: Handle multiple br tags
        handle_br_tags(soup)

        # Step 6: Remove divs that contain only br tags and whitespace
        remove_only_br_divs(soup)

        # Step 7: Add classes to specified tags
        add_classes_to_tags(soup, tags_with_classes)

        # Get HTML string
        html_output = str(soup)

        # Post-processing for <br/> tags to make them <br> for compatibility
        return html_output.replace("<br/>", "<br>")
    except Exception as e:  # noqa: BLE001
        log.error("Error cleaning HTML: %s", e)
        return input_html


def process_tags(
    soup: BeautifulSoup,
    allowed_tags: Iterable[str],
) -> None:
    """Process all tags, keeping only those in the whitelist and removing class/style attributes.

    Args:
        soup: BeautifulSoup object to process
        allowed_tags: Set of tags to keep
    """
    allowed_tags_set = set(allowed_tags)

    # First collect all non-whitelisted tags to process
    tags_to_process = []
    for tag in soup.find_all():
        if tag.name not in allowed_tags_set:  # type: ignore
            tags_to_process.append(tag)

    # Process in reverse order to handle nested tags correctly (inner to outer)
    for tag in reversed(tags_to_process):
        # Unwrap the tag (remove tag but keep its contents)
        tag.unwrap()  # type: ignore

    # Remove class and style attributes from all remaining tags
    for tag in soup.find_all():
        if not isinstance(tag, Tag):
            continue

        # Remove class and style attributes
        if "class" in tag.attrs:
            del tag["class"]
        if "style" in tag.attrs:
            del tag["style"]


def add_classes_to_tags(soup: BeautifulSoup, tags_with_classes: dict[str, str]) -> None:
    """Add specified classes to tags.

    Args:
        soup: BeautifulSoup object to process
        tags_with_classes: Dict mapping tags to classes to add
    """
    for tag_name, classes_str in tags_with_classes.items():
        classes_to_add = classes_str.split()

        for tag in soup.find_all(tag_name):
            if not isinstance(tag, Tag):
                continue

            tag["class"] = classes_to_add  # type: ignore


def remove_empty_tags(soup: BeautifulSoup, tag_name: str) -> None:
    """Remove empty tags of the specified type.

    Args:
        soup: BeautifulSoup object to process
        tag_name: Tag name to check for emptiness
    """
    for tag in soup.find_all(tag_name):
        # Check if tag contains only whitespace
        if tag.get_text(strip=True) == "":
            tag.decompose()


def is_only_br_and_whitespace(tag: Tag) -> bool:
    """Check if tag contains only br tags and whitespace.

    Args:
        tag: BeautifulSoup Tag to check

    Returns:
        True if tag contains only br tags and whitespace, False otherwise
    """
    # Get all non-br elements (excluding whitespace text nodes)
    non_br_elements = [
        child
        for child in tag.contents
        if (isinstance(child, Tag) and child.name != "br")
        or (not isinstance(child, Tag) and child.strip())  # type: ignore
    ]

    # If we have no non-br elements, this tag has only br tags and whitespace
    return len(non_br_elements) == 0


def remove_only_br_divs(soup: BeautifulSoup) -> None:
    """Remove divs that contain only br tags and whitespace.

    Args:
        soup: BeautifulSoup object to process
    """
    # Process recursively from bottom up to handle nested divs
    found_changes = True
    while found_changes:
        found_changes = False
        for div in soup.find_all("div"):
            if isinstance(div, Tag) and is_only_br_and_whitespace(div):  # isinstance fo mypy
                div.decompose()
                found_changes = True
                break


def handle_br_tags(soup: BeautifulSoup) -> None:
    """Handle multiple consecutive <br> tags, keeping only the first one.

    This function looks for consecutive <br> tags in the document and
    keeps only one of them. It also handles complex cases inside <p> tags.

    Args:
        soup: BeautifulSoup object to process
    """
    for tag in soup.find_all():
        if not isinstance(tag, Tag):
            continue

        # Get all children as a list
        contents = list(tag.children)

        # Look for <br> tags with only whitespace in between
        to_remove = []
        last_was_br = False

        for child in contents:
            if isinstance(child, Tag) and child.name == "br":
                if last_was_br:
                    # This is a consecutive <br>, mark for removal
                    to_remove.append(child)
                last_was_br = True
            elif isinstance(child, str) and child.strip() == "":
                # This is whitespace, preserve last_was_br state
                pass
            else:
                # This is content, reset the state
                last_was_br = False

        # Remove the consecutive br tags
        for br_tag in to_remove:
            br_tag.decompose()
