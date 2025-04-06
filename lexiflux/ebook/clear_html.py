import logging
from collections.abc import Iterable

from bs4 import BeautifulSoup, Comment, Tag

log = logging.getLogger(__name__)


def clear_html(  # noqa: PLR0913
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
    keep_empty_tags: Iterable[str] = (
        "img",
        "hr",
        "br",
        "iframe",
    ),
    ids_to_keep: Iterable[str] = (),
    tags_with_classes: dict[str, str] | None = None,
) -> str:
    """Clean HTML by keeping only whitelisted tags and removing class/style attributes
    and reducing sequences of <br> into single <br>.

    Args:
        input_html: The HTML string to clean
        allowed_tags: Whitelist of tags that should be kept, others will be removed keeping content,
            except for tags tags_to_remove_with_content which will be removed along
            with their content.
        tags_to_remove_with_content: Tags that should be removed along with their content
        keep_empty_tags: Tags that should be kept even when they have no content. all other tags
            without content will be removed
        ids_to_keep: List of element IDs that should be preserved regardless of tag type
        tags_with_classes: Dict mapping tags to classes to add

    Returns:
        Cleaned HTML string with only allowed tags and without class/style attributes
    """
    if not input_html:
        return ""
    new_lines_table = str.maketrans(
        {
            "\r": " ",
            "\n": " ",
        },
    )
    input_html = input_html.translate(new_lines_table)

    if tags_with_classes is None:
        tags_with_classes = {
            "h1": "display-4 fw-semibold text-primary mb-4",
            "h2": "display-5 fw-semibold text-secondary mb-3",
            "h3": "h3 fw-normal text-dark mb-3",
            "h4": "h4 fw-normal text-dark mb-2",
            "h5": "h5 fw-normal text-dark mb-2",
        }

    try:
        soup = BeautifulSoup(input_html, "lxml")

        delete_comments(soup)
        delete_tags(soup, tags_to_remove_with_content)
        unwrap_tags(
            soup=soup,
            allowed_tags=allowed_tags,
            ids_to_keep=ids_to_keep,
        )
        remove_styles(soup)
        remove_empty_tags(soup, allowed_tags, keep_empty_tags, ids_to_keep)
        remove_consecutive_br_tags(soup)
        add_classes_to_tags(soup, tags_with_classes)

        return str(soup).replace("<br/>", "<br>")
    except Exception as e:  # noqa: BLE001
        log.error("Error cleaning HTML: %s", e)
        return input_html


def delete_tags(soup, tags_to_remove_with_content):
    for tag_name in tags_to_remove_with_content:
        for tag in soup.find_all(tag_name):
            tag.decompose()


def delete_comments(soup):
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()


def unwrap_tags(
    soup: BeautifulSoup,
    allowed_tags: Iterable[str],
    ids_to_keep: Iterable[str] = (),
) -> None:
    """Delete tags keeping content. Except those in the `allowed_tags` or with `ids_to_keep`.

    Args:
        soup: BeautifulSoup object to process
        allowed_tags: Set of tags to keep
        ids_to_keep: IDs of elements to preserve regardless of tag type
    """
    allowed_tags_set = set(allowed_tags)
    ids_to_keep_set = set(ids_to_keep)

    # First collect all non-whitelisted tags to process
    tags_to_process = []
    for tag in soup.find_all():
        if not isinstance(tag, Tag):
            continue

        if "id" in tag.attrs and tag["id"] in ids_to_keep_set:
            continue

        if tag.name not in allowed_tags_set:
            tags_to_process.append(tag)

    # Unwrap in reverse order to handle nested tags correctly (inner to outer)
    for tag in reversed(tags_to_process):
        # Unwrap the tag (remove tag but keep its contents)
        tag.unwrap()  # type: ignore


def remove_styles(soup):
    """Remove class and style attributes."""
    for tag in soup.find_all():
        if not isinstance(tag, Tag):
            continue

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


def remove_consecutive_br_tags(soup: BeautifulSoup) -> None:
    """From <br> tags sequence, keep only the first one."""
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


def has_content(tag: Tag, keep_empty_tags: set[str]) -> bool:
    """Check if a tag has meaningful content or is a tag that should be kept even when empty.

    Args:
        tag: Tag to check
        keep_empty_tags: Set of tag names that should be kept even when empty

    Returns:
        True if tag has content or should be kept, False otherwise
    """
    # If it's a tag that should be kept even if empty, return True
    if tag.name in keep_empty_tags:
        return True

    # If it has meaningful text content, return True
    if tag.get_text(strip=True):
        return True

    # If it contains any tags that should be kept even if empty, return True
    return any(tag.find(empty_tag) for empty_tag in keep_empty_tags)


def remove_empty_tags(
    soup: BeautifulSoup,
    allowed_tags: Iterable[str],
    keep_empty_tags: Iterable[str],
    ids_to_keep: Iterable[str],
) -> None:
    """Remove empty tags from the whitelist (except those in keep_empty_tags).

    Args:
        soup: BeautifulSoup object to process
        allowed_tags: Whitelist of tags that should be kept
        keep_empty_tags: Set of tag names that should be kept even when empty
        ids_to_keep: IDs of elements to preserve regardless of content
    """
    # Convert to sets for faster lookup
    allowed_tags_set = set(allowed_tags)
    keep_empty_tags_set = set(keep_empty_tags)
    ids_to_keep_set = set(ids_to_keep)

    # Process recursively until no changes are found
    found_changes = True
    while found_changes:
        found_changes = False

        for tag in soup.find_all():
            if not isinstance(tag, Tag):
                continue

            if tag.name not in allowed_tags_set:
                # not whitelisted tags will be removed anyway
                continue

            if "id" in tag.attrs and tag["id"] in ids_to_keep_set:
                continue

            if not has_content(tag, keep_empty_tags_set):
                tag.decompose()
                found_changes = True
                break

            # Case 1: Tag contains only br tags and whitespace (former remove_only_br_divs logic)
            if tag.name == "div" and is_only_br_and_whitespace(tag):
                tag.decompose()
                found_changes = True
                break
