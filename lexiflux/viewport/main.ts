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
  // Encode the selected text to be safely included in a URL
  const encodedText = encodeURIComponent(selectedText);

  // Construct the URL with the encoded selected text as a query parameter
  const url = `/translate?text=${encodedText}`;

  // Send the GET request
  fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.text();
    })
    .then(translatedText => {
      // Handle the translated text (e.g., display it in the UI)
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
  let selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    // Create a new span for the translation and the selected text
    let translationSpan = document.createElement('span');
    translationSpan.className = 'translation-span';

    // Create a div for the translation
    let translationDiv = document.createElement('div');
    translationDiv.className = 'translation-text';
    translationDiv.textContent = translatedText;

    // Create a div for the original text
    let originalTextDiv = document.createElement('div');
    originalTextDiv.className = 'original-text';
    originalTextDiv.textContent = selectedText;

    // Append the translation and original text to the span
    translationSpan.appendChild(translationDiv);
    translationSpan.appendChild(originalTextDiv);

    // Replace the selected text with the new span
    range.deleteContents();
    range.insertNode(translationSpan);
  }
}

function handleWordClick(event: MouseEvent): void {
  let clickedWordSpan = event.target as HTMLElement;

  // Check if the clicked word is already translated
  if (clickedWordSpan.classList.contains('translated')) {
    // Remove the translation
    clickedWordSpan.classList.remove('translated');
    if (typeof clickedWordSpan.dataset.originalText === 'string') {
      clickedWordSpan.innerHTML = clickedWordSpan.dataset.originalText;
    }
  } else {
    // Treat the click as a selection and translate the word
    let selectedText = clickedWordSpan.textContent;
    if (selectedText) {
      let range = document.createRange();
      range.selectNode(clickedWordSpan);
      sendTranslationRequest(selectedText, range);
    }
  }
}

function handleWordContainerClick(event: MouseEvent): void {
    // Check if the clicked element is a word span
    if (event.target && (event.target as HTMLElement).classList.contains('word')) {
        handleWordClick(event as MouseEvent);
    }
}

function handleMouseUpEvent(): void {
  log('Mouse up event triggered.');
  let selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    let range = selection.getRangeAt(0);
    let selectedText = range.toString();
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
