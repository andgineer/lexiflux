import { viewport } from './viewport';
import {log} from './utils';
import { sendTranslationRequest, lexicalPanelSwitched, clearLexicalPanel } from './translate';

const CLICK_TIMEOUT_MS = 200;

// to make it available in HTML page
(window as any).goToPage = goToPage;

let clickTimeout: NodeJS.Timeout | null = null;

async function goToPage(pageNum: number, topWord: number): Promise<void> {
        await viewport.loadPage(pageNum, topWord);
//         reInitDom();
}

async function handlePrevButtonClick(): Promise<void> {
    await viewport.scrollUp();
//     reInitDom();
}

async function handleNextButtonClick(): Promise<void> {
    await viewport.scrollDown();
//     reInitDom();
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
    const parent = translationSpan.parentNode;
    if (parent) {
        // Remove the translation text div
        const translationTextDiv = translationSpan.querySelector('.translation-text');
        if (translationTextDiv) {
            translationTextDiv.remove();
        }

        // Move all child nodes of the translation span to the parent
        while (translationSpan.firstChild) {
            parent.insertBefore(translationSpan.firstChild, translationSpan);
        }

        // Remove the empty translation span
        translationSpan.remove();
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

function handleMouseUpEvent(event: MouseEvent): void {
  log('Mouse up event triggered.');

  // Check if the click was on a translation span
  const clickedElement = event.target as HTMLElement;
  const translationSpan = clickedElement.closest('.translation-span');

  if (translationSpan) {
    // If clicked on a translation span, remove it
    restoreOriginalSpans(translationSpan as HTMLElement);
    return; // Exit the function early
  }

  // If not clicked on a translation span, proceed with regular selection handling
  let selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    let range = selection.getRangeAt(0);

    // If the selection is within a single word, expand it to include the whole word
    if (range.startContainer === range.endContainer && range.startContainer.nodeType === Node.TEXT_NODE) {
      let wordElement = range.startContainer.parentElement;
      if (wordElement && wordElement.classList.contains('word')) {
        range.selectNodeContents(wordElement);
      }
    }

    // Only proceed if the selection is not empty
    if (!range.collapsed) {
      clearLexicalPanel();
      sendTranslationRequest(range);
    }
  }
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

    const tabElements = document.querySelectorAll('#lexicalPanelTabs button[data-bs-toggle="tab"]');
    tabElements.forEach(tabElement => {
        tabElement.addEventListener('shown.bs.tab', function(event: Event) {
            const target = event.target as HTMLElement;
            if (target && target.id) {
                lexicalPanelSwitched(target.id);
            }
        });
    });

    const infoPanel = document.getElementById('lexical-panel');
    if (infoPanel) {
        infoPanel.addEventListener('shown.bs.collapse', function() {
            const activeTab = document.querySelector('#lexicalPanelTabs .nav-link.active') as HTMLElement;
            if (activeTab && activeTab.id) {
                lexicalPanelSwitched(activeTab.id);
            }
        });
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
