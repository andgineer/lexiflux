import { viewport } from './viewport';
import { log, showModal, closeModal } from './utils';
import { sendTranslationRequest, lexicalPanelSwitched, clearLexicalPanel, hideTranslation } from './translate';
import { initializeReaderSettings, initializeReaderEventListeners } from './readerSettings';

const CLICK_TIMEOUT_MS = 200;

// to make it available in HTML page
(window as any).goToPage = goToPage;
(window as any).jump = jump;

let clickTimeout: NodeJS.Timeout | null = null;

async function handlePrevButtonClick(): Promise<void> {
    await viewport.scrollUp();
}

async function handleNextButtonClick(): Promise<void> {
    await viewport.scrollDown();
}

async function jump(pageNum: number, topWord: number): Promise<void> {
    await viewport.jump(pageNum, topWord);
}

async function handleBackButtonClick(): Promise<void> {
    await viewport.jumpBack();
}

async function handleForwardButtonClick(): Promise<void> {
    await viewport.jumpForward();
}

function handleWordClick(event: MouseEvent): void {
  let clickedElement = event.target as HTMLElement;

  // Check if clicked on the translation text
  if (clickedElement.classList.contains('translation-text')) {
    let translationSpan = clickedElement.closest('.translation-span') as HTMLElement | null;
    if (translationSpan) {
      hideTranslation(translationSpan);
    }
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
    hideTranslation(translationSpan as HTMLElement);
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

function handleSideBarSettingsButtonClick(event: MouseEvent): void {
    event.preventDefault();
    window.location.href = '/language-preferences/';
}

async function goToPage(pageNum: number, topWord: number): Promise<void> {
    await viewport.jump(pageNum, topWord);
}



function handleGoToPageButtonClick(event: Event): void {
    event.preventDefault();
    showModal('goToPageModal');
}

function handleModalSubmit(modalId: string, inputId: string, action: (value: string) => void): void {
    const modal = document.getElementById(modalId);
    const input = document.getElementById(inputId) as HTMLInputElement;
    if (modal && input) {
        const value = input.value.trim();
        if (value) {
            action(value);
            input.value = '';
            closeModal(modalId);
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

    let backButton = document.getElementById('back-button');
    if (backButton) {
        backButton.removeEventListener('click', handleBackButtonClick);
        backButton.addEventListener('click', handleBackButtonClick);
    }

    let forwardButton = document.getElementById('forward-button');
    if (forwardButton) {
        forwardButton.removeEventListener('click', handleForwardButtonClick);
        forwardButton.addEventListener('click', handleForwardButtonClick);
    }

    let gearButton = document.getElementById('sidebar-settings');
    if (gearButton) {
        gearButton.removeEventListener('click', handleSideBarSettingsButtonClick);
        gearButton.addEventListener('click', handleSideBarSettingsButtonClick);
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

    let goToPageButton = document.getElementById('page-number');
    if (goToPageButton) {
        goToPageButton.removeEventListener('click', handleGoToPageButtonClick);
        goToPageButton.addEventListener('click', handleGoToPageButtonClick);
    }

    // Close buttons for modals
    document.querySelectorAll('.modal .btn-close').forEach((closeButton) => {
        closeButton.addEventListener('click', () => {
            const modal = closeButton.closest('.modal') as HTMLElement;
            if (modal) {
                closeModal(modal.id);
            }
        });
    });

    const goToPageSubmit = document.getElementById('goToPageSubmit');
    if (goToPageSubmit) {
        goToPageSubmit.addEventListener('click', () => {
            handleModalSubmit('goToPageModal', 'pageNumberInput', (value) => {
                const pageNum = parseInt(value);
                if (!isNaN(pageNum)) {
                    goToPage(pageNum, 0);
                }
            });
        });
    }

    // Initialize modals as hidden
    document.querySelectorAll('.modal').forEach((modal) => {
        if (modal instanceof HTMLElement) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    });
    initializeReaderEventListeners();
}

// Close modal when clicking outside of it
window.onclick = function(event: MouseEvent) {
    if (event.target instanceof Element && event.target.classList.contains('modal')) {
        closeModal(event.target.id);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const topWord = parseInt(document.body.getAttribute('data-top-word') || '0');
    viewport.loadPage(viewport.pageNumber, topWord).then(() => {
        reInitDom();
        initializeReaderSettings();
    }).catch((error: Error) => {
        console.error('Failed to load page:', error);
    });
});
