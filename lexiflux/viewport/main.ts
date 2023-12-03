import {
    loadPage,
    findViewport,
    renderWordsContainer,
    reportVieportChange,
    initializeVariables,
    getPageNum,
    getTotalWords,
    getTopWord,
    getBookId,
    getLastAddedWordIndex,
    getWordsContainer,
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
        reportVieportChange();
    } else {
        findViewport(getTopWord() - 1);
        reportVieportChange();
    }
}

async function handleNextButtonClick(): Promise<void> {
    let lastWordIndex: number = getLastAddedWordIndex();
    if (lastWordIndex >= getTotalWords() - 1) {
        await loadPage(getPageNum() + 1);
        renderWordsContainer(0);
        reInitDom();
        reportVieportChange();
    } else {
        renderWordsContainer(lastWordIndex + 1);
        reportVieportChange();
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

function sendTranslationRequest(selectedText: string, range: Range): void {
  const encodedText = encodeURIComponent(selectedText);
  const url = `/translate?text=${encodedText}`;

  fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.text();
    })
    .then(translatedText => {
      log('Translated text:', translatedText);
      displayTranslation(selectedText, translatedText, range);
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
      }
    })
    .catch(error => {
      console.error('Error during translation:', error);
    });
}

function displayTranslation(selectedText: string, translatedText: string, range: Range): void {
  // Create a container to hold the original elements
  let originalElementsContainer = document.createElement('div');

  // Clone and append each element in the range to the container
  range.cloneContents().childNodes.forEach(node => {
    originalElementsContainer.appendChild(node.cloneNode(true));
  });

  let translationSpan = document.createElement('span');
  translationSpan.className = 'translation-span';
  translationSpan.dataset.originalHtml = originalElementsContainer.innerHTML; // Store original HTML

  let translationDiv = document.createElement('div');
  translationDiv.className = 'translation-text';
  translationDiv.textContent = translatedText;

  let originalTextDiv = document.createElement('div');
  originalTextDiv.className = 'original-text';
  originalTextDiv.textContent = selectedText;

  translationSpan.appendChild(translationDiv);
  translationSpan.appendChild(originalTextDiv);

  range.deleteContents();
  range.insertNode(translationSpan);
}

function handleWordClick(event: MouseEvent): void {
  let clickedElement = event.target as HTMLElement;

  // Find the closest translation span
  let translationSpan = clickedElement.closest('.translation-span') as HTMLElement | null;
  if (translationSpan) {
    restoreOriginalSpans(translationSpan);
  } else {
    // Handle new translation
    let selectedText = clickedElement.textContent;
    if (selectedText) {
      let range = document.createRange();
      range.selectNode(clickedElement);
      sendTranslationRequest(selectedText, range);
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
        }
      });
      translationSpan.remove();
    }
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
    let selectedText = range.toString();

    // Check if the selection includes a translated word
    let containerElement = range.commonAncestorContainer as HTMLElement;
    let translationSpan = containerElement.closest('.translation-span') as HTMLElement | null;
    if (translationSpan) {
      restoreOriginalSpans(translationSpan);
    }

    if (selectedText) {
      sendTranslationRequest(selectedText, range);
    }
  }
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
