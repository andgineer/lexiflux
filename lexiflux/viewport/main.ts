import { viewport } from './viewport';
import {log} from './utils';
import { sendTranslationRequest } from './translate';

const CLICK_TIMEOUT_MS = 200;

// to make it available in HTML page
(window as any).goToPage = goToPage;

let clickTimeout: NodeJS.Timeout | null = null;

async function goToPage(pageNum: number, topWord: number): Promise<void> {
        await viewport.loadPage(pageNum, topWord);
        reInitDom();
}

async function handlePrevButtonClick(): Promise<void> {
    await viewport.scrollUp();
    reInitDom();
}

async function handleNextButtonClick(): Promise<void> {
    await viewport.scrollDown();
    reInitDom();
}

function handleWordClick(event: MouseEvent): void {
  let clickedElement = event.target as HTMLElement;

  // Check if clicked on the translation text
  if (clickedElement.classList.contains('translation-text')) {
    let translationSpan = clickedElement.closest('.translation-span') as HTMLElement | null;
    if (translationSpan) {
      restoreOriginalSpans(translationSpan);
    }
  }
}

function restoreOriginalSpans(translationSpan: HTMLElement): void {
  let originalHtml = translationSpan.dataset.originalHtml;
  if (originalHtml) {
    let tempContainer = document.createElement('div');
    tempContainer.innerHTML = originalHtml;

    const parent = translationSpan.parentNode;
    if (parent) {
      // Replace the translation span with the original spans
      Array.from(tempContainer.childNodes).forEach(child => {
        if (child instanceof HTMLElement) {
          parent.insertBefore(child, translationSpan);
          const space = document.createTextNode(' ');
          parent.insertBefore(space, translationSpan);
        }
      });
      translationSpan.remove();
    }

    // separate copy
    tempContainer = document.createElement('div');
    tempContainer.innerHTML = originalHtml;
  }
}

function handleWordContainerClick(event: MouseEvent): void {
    let target = event.target as HTMLElement;

    // Check if the target or its parent is a word or a translation
    if (target.classList.contains('word') || target.classList.contains('translation-text') || target.closest('.translation-span')) {
        if (clickTimeout !== null) {
            // If a timer is already running, this is a double click
            clearTimeout(clickTimeout);
            clickTimeout = null;
            handleDblClick(event);
        } else {
            // Start a timer to call the single click handler
            clickTimeout = setTimeout(() => {
                handleWordClick(event);
                clickTimeout = null;
            }, CLICK_TIMEOUT_MS); // 200 ms delay
        }
    }
}

function handleMouseUpEvent(): void {
  log('Mouse up event triggered.');
  let selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    let range = selection.getRangeAt(0);
    let selectedWordSpans = getSelectedWordSpans(range);
    let selectedText = selectedWordSpans.map(span => span.textContent).join(' ');
    log('Selected text:', selectedText);

    if (selectedText) {
      sendTranslationRequest(selectedText, range, selectedWordSpans);
    }
  }
}

function getSelectedWordSpans(range: Range): HTMLElement[] {
    let startNode: Node = range.startContainer;
    let endNode: Node = range.endContainer;

    // Adjust startNode to include the word span if the selection starts partway through it
    if (startNode.nodeType !== Node.ELEMENT_NODE) {
        startNode = startNode.parentNode || startNode;
    }

    // If startNode is an element but not a word span, find the next word span
    if (startNode instanceof HTMLElement && !startNode.classList.contains('word')) {
        // Find the next word span by traversing next siblings
        let nextWordSpan = startNode.nextElementSibling;
        while (nextWordSpan && !nextWordSpan.classList.contains('word')) {
            nextWordSpan = nextWordSpan.nextElementSibling;
        }
        startNode = nextWordSpan || startNode;
    }

    // Adjust endNode to include the word span if the selection ends partway through it
    if (endNode.nodeType !== Node.ELEMENT_NODE) {
        endNode = endNode.parentNode || endNode;
    }
    if (endNode instanceof HTMLElement && !endNode.classList.contains('word')) {
        let prevWordSpan = endNode.previousElementSibling;
        while (prevWordSpan && !prevWordSpan.classList.contains('word')) {
            prevWordSpan = prevWordSpan.previousElementSibling;
        }
        endNode = prevWordSpan || endNode;
    }

    let selectedWordSpans: HTMLElement[] = [];
    let currentNode: Node | null = startNode;

    // Traverse the DOM from the start node to the end node
    while (currentNode && currentNode !== endNode) {
        if (currentNode instanceof HTMLElement && currentNode.classList.contains('word')) {
            selectedWordSpans.push(currentNode);
        }
        currentNode = getNextNode(currentNode);
    }

    // Include the end node if it's a word span
    if (endNode instanceof HTMLElement && endNode.classList.contains('word')) {
        selectedWordSpans.push(endNode);
    }

    return selectedWordSpans;
}


function handleDblClick(event: MouseEvent): void {
    let clickedElement = event.target as HTMLElement;

    // Check if clicked on a word or a translation text
    if (clickedElement.classList.contains('word') || clickedElement.classList.contains('translation-text')) {
        let text = clickedElement.textContent || '';
        let url = 'https://glosbe.com/sr/ru/' + encodeURIComponent(text);
        window.open(url, '_blank');
    }
}

function getNextNode(node: Node): Node | null {
  if (node.firstChild) {
    return node.firstChild;
  }
  while (node) {
    if (node.nextSibling) {
      return node.nextSibling;
    }
    if (node.parentNode) {
      node = node.parentNode;
    }
  }
  return null;
}

function reInitDom(): void {
    log('reInitDom called');
    let prevButton = document.getElementById('prev-button');
    if (prevButton) {
        prevButton.removeEventListener('click', handlePrevButtonClick);
        prevButton.addEventListener('click', handlePrevButtonClick);
    }

    let nextButton = document.getElementById('next-button');
    if (nextButton) {
        nextButton.removeEventListener('click', handleNextButtonClick);
        nextButton.addEventListener('click', handleNextButtonClick);
    }

    const wordsContainer = viewport.getWordsContainer();
    if (wordsContainer) {
        wordsContainer.removeEventListener('mouseup', handleMouseUpEvent);
        wordsContainer.addEventListener('mouseup', handleMouseUpEvent);

        wordsContainer.removeEventListener('click', handleWordContainerClick);
        wordsContainer.addEventListener('click', handleWordContainerClick);

        wordsContainer.removeEventListener('dblclick', handleDblClick);
        wordsContainer.addEventListener('dblclick', handleDblClick);

    } else {
        console.error('Could not find words container');
    }
}

document.body.addEventListener('htmx:configRequest', (event: Event) => {
    const detail = (event as CustomEvent).detail;
    detail.parameters['book-page-number'] = viewport.pageNumber;
    detail.parameters['book-code'] = viewport.bookCode;
});

document.addEventListener('DOMContentLoaded', () => {
    viewport.loadPage(viewport.pageNumber, 0).then(() => {
        reInitDom();
    }).catch((error: Error) => {
        console.error('Failed to load page:', error);
    });
});
