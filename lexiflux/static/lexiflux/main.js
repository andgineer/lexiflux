const {
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
} = require('./viewport.js');

const { log } = require('./utils.js');

let resizeTimeout;

async function handlePrevButtonClick() {
    if (getTopWord() === 0) {
        // Already at the beginning of the page, load the previous page
        if (getPageNum() === 1) {
            // Already at the beginning of the book, do nothing
            return;
        }
        await loadPage(getPageNum() - 1);
        findViewport(getTotalWords() - 1);
        reInitDom();
        reportVieportChange();
        return;
    }
    findViewport(getTopWord() - 1);
    reportVieportChange();
}

async function handleNextButtonClick() {
    let lastWordIndex = getLastAddedWordIndex();
    if (lastWordIndex >= getTotalWords() - 1) {
        // Last word is already visible, load the next page
        await loadPage(getPageNum() + 1);
        renderWordsContainer(0);
        reInitDom();
        reportVieportChange();
        return;
    }
    renderWordsContainer(lastWordIndex + 1);
    reportVieportChange();
}

function handleResize() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function() {
        renderWordsContainer();
    }, 50);
}

function handleHtmxAfterSwap(event) {
    if (event.detail.trigger && event.detail.trigger.classList.contains('word')) {
        setTimeout(function() {
            renderWordsContainer();
        }, 50);
    }
}

function reInitDom() {
    // Reattach event listener to the previous button
    let prevButton = document.getElementById('prev-button');
    if (prevButton) {
        prevButton.removeEventListener('click', handlePrevButtonClick);
        prevButton.addEventListener('click', handlePrevButtonClick);
    }

    // Reattach event listener to the next button
    let nextButton = document.getElementById('next-button');
    if (nextButton) {
        nextButton.removeEventListener('click', handleNextButtonClick);
        nextButton.addEventListener('click', handleNextButtonClick);
    }
}

window.addEventListener('resize', handleResize);

document.body.addEventListener('htmx:afterSwap', handleHtmxAfterSwap);

document.body.addEventListener('htmx:configRequest', function(event) {
    // Add page and book parameters to all HTMX requests
    event.detail.parameters['page-num'] = getPageNum();
    event.detail.parameters['book-id'] = getBookId();
    event.detail.parameters['top-word'] = getTopWord();
});

document.addEventListener('DOMContentLoaded', function() {
    initializeVariables();
    loadPage(getPageNum()).then(() => {
        log('Page loaded successfully.');
        renderWordsContainer(0);
        reInitDom();
    }).catch(error => {
        console.error('Failed to load page:', error);
    });
});
