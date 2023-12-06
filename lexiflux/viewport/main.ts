import {
    loadPage,
    findViewport,
    renderWordsContainer,
    reportReadingPosition,
    initializeVariables,
    getPageNum,
    getTotalWords,
    getTopWord,
    getBookId,
    getLastAddedWordIndex,
    getWordsContainer,
    getWordSpans,
} from './viewport';

import { log } from './utils';

let resizeTimeout: NodeJS.Timeout;

async function handlePrevButtonClick(): Promise<void> {
    if (getTopWord() === 0) {
        if (getPageNum() === 1) {
            return;
        }
        await loadPage(getPageNum() - 1);
        findViewport(getTotalWords() - 1);
        reInitDom();
        reportReadingPosition();
    } else {
        findViewport(getTopWord() - 1);
        reportReadingPosition();
    }
}

async function handleNextButtonClick(): Promise<void> {
    let lastWordIndex: number = getLastAddedWordIndex();
    if (lastWordIndex >= getTotalWords() - 1) {
        await loadPage(getPageNum() + 1);
        renderWordsContainer(0);
        reInitDom();
        reportReadingPosition();
    } else {
        renderWordsContainer(lastWordIndex + 1);
        reportReadingPosition();
    }
}

function handleResize(): void {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        renderWordsContainer();
    }, 150);
}

function handleHtmxAfterSwap(event: Event): void {
    let detail = (event as CustomEvent).detail;
    if (detail.trigger && detail.trigger.classList.contains('word')) {
        setTimeout(() => {
            renderWordsContainer();
        }, 150);
    }
}


interface TranslationResponse {
  translatedText: string;
}

function sendTranslationRequest(selectedText: string, range: Range, selectedWordSpans: HTMLElement[]): void {
  const encodedText = encodeURIComponent(selectedText);
  const url = `/translate?text=${encodedText}`;

  fetch(url)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
    .then((data: { translatedText: string; article: string }) => {
      log('Translated:', data);
      const sidebar = document.getElementById('sidebar');
      if (sidebar) {
        sidebar.innerHTML = data.article; // Set innerHTML only if sidebar is not null
      } else {
        console.error('Sidebar element not found');
      }
      createAndReplaceTranslationSpan(selectedText, data.translatedText, selectedWordSpans);
      renderWordsContainer();
    })
    .catch(error => {
      console.error('Error during translation:', error);
    });
}

function createAndReplaceTranslationSpan(selectedText: string, translatedText: string, selectedWordSpans: HTMLElement[]): void {
  let firstWordSpan = selectedWordSpans[0];
  let translationSpan = document.createElement('span');
  translationSpan.dataset.originalHtml = selectedWordSpans.map(span => span.outerHTML).join('');
  translationSpan.className = 'translation-span';
  translationSpan.id = 'translation-' + firstWordSpan.id;

  let translationDiv = document.createElement('div');
  translationDiv.className = 'translation-text';
  translationDiv.textContent = translatedText;

  let textDiv = document.createElement('div');
  textDiv.className = 'text';
  textDiv.textContent = selectedText;

  translationSpan.appendChild(translationDiv);
  translationSpan.appendChild(textDiv);

  getWordsContainer().insertBefore(translationSpan, firstWordSpan);
  const wordSpans = getWordSpans();
  wordSpans.splice(wordSpans.indexOf(firstWordSpan), 0, translationSpan);

  // Remove the original word spans
  selectedWordSpans.forEach(span => {
    getWordsContainer().removeChild(span);
  });

  selectedWordSpans.forEach(span => {
    const index = wordSpans.indexOf(span);
    if (index !== -1) {
        wordSpans.splice(index, 1); // Remove the original word span
    }
  });
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

function removeTranslationsInRange(range: Range): void {
  // Get the common ancestor container of the range
  let commonAncestor = range.commonAncestorContainer;
  let containerElement = commonAncestor.nodeType === Node.ELEMENT_NODE
    ? commonAncestor as Element
    : commonAncestor.parentElement;

  if (containerElement) {
    // Find all translation spans within the container
    const translationSpans = containerElement.querySelectorAll('.translation-span');

    translationSpans.forEach((span: Element) => {
      // Check if the translation span is within or intersects the range
      if (isSpanInRange(span, range)) {
        span.remove(); // Remove the translation span
      }
    });
  }
}

function isSpanInRange(span: Element, range: Range): boolean {
  let spanRange = document.createRange();
  spanRange.selectNode(span);
  return range.intersectsNode(span);
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
        }
      });
      translationSpan.remove();
    }

    // separate copy
    tempContainer = document.createElement('div');
    tempContainer.innerHTML = originalHtml;
    const originalSpans = Array.from(tempContainer.childNodes).filter(node => node.nodeType === Node.ELEMENT_NODE) as HTMLElement[];

    // Update the wordSpans array
    const wordSpans = getWordSpans();
    const index = wordSpans.indexOf(translationSpan);
    if (index !== -1) {
        wordSpans.splice(index, 1); // Remove the translation span
        wordSpans.splice(index, 0, ...originalSpans); // Insert the original word spans
    }
    renderWordsContainer();
  }
}

function handleWordContainerClick(event: MouseEvent): void {
    let target = event.target as HTMLElement;

    // Check if the target or its parent is a word or a translation
    if (target.classList.contains('word') || target.classList.contains('translation-text') || target.closest('.translation-span')) {
        handleWordClick(event);
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

    const wordsContainer = getWordsContainer();
    if (wordsContainer) {
        wordsContainer.removeEventListener('mouseup', handleMouseUpEvent);
        wordsContainer.addEventListener('mouseup', handleMouseUpEvent);

        wordsContainer.removeEventListener('click', handleWordContainerClick);
        wordsContainer.addEventListener('click', handleWordContainerClick);
    } else {
        console.error('Could not find words container');
    }
}

window.addEventListener('resize', handleResize);

document.body.addEventListener('htmx:afterSwap', handleHtmxAfterSwap);

document.body.addEventListener('htmx:configRequest', (event: Event) => {
    let detail = (event as CustomEvent).detail;
    detail.parameters['page-num'] = getPageNum();
    detail.parameters['book-id'] = getBookId();
    detail.parameters['top-word'] = getTopWord();
});

document.addEventListener('DOMContentLoaded', () => {
    initializeVariables();
    let pageNum = getPageNum();
    loadPage(pageNum).then(() => {
        renderWordsContainer(0);
        reInitDom();
    }).catch((error: Error) => {
        console.error('Failed to load page:', error);
    });
});
