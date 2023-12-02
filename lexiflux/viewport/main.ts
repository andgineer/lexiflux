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
    getLastAddedWordIndex
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

function reInitDom(): void {
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
    loadPage(getPageNum()).then(() => {
        log('Page loaded successfully.');
        renderWordsContainer(0);
        reInitDom();
    }).catch((error: Error) => {
        console.error('Failed to load page:', error);
    });
});
