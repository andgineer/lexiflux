
async function handlePrevButtonClick() {
    if (topWord === 0) {
        // Already at the beginning of the page, load the previous page
        if (pageNum === 1) {
            // Already at the beginning of the book, do nothing
            return;
        }
        await loadPage(pageNum - 1);
        findViewport(totalWords - 1);
        reportVieportChange();
        return;
    }
    findViewport(topWord - 1);
    reportVieportChange();
}

async function handleNextButtonClick() {
    let lastWordIndex = lastAddedWordIndex;
    if (lastWordIndex >= totalWords - 1) {
        // Last word is already visible, load the next page
        await loadPage(pageNum + 1);
        renderWordsContainer(0);
        reportVieportChange();
        return;
    }
    renderWordsContainer(lastWordIndex + 1);
    reportVieportChange();
}

function handleResize() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function() {
        fillWordsContainer(topWord);
    }, 50);
}

function handleHtmxAfterSwap(event) {
    if (event.detail.trigger && event.detail.trigger.classList.contains('word')) {
        setTimeout(function() {
            fillWordsContainer(topWord);
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

    wordsContainer = document.getElementById('words-container');
}

window.addEventListener('resize', handleResize);

document.body.addEventListener('htmx:afterSwap', handleHtmxAfterSwap);

document.body.addEventListener('htmx:configRequest', function(event) {
    // Add page and book parameters to all HTMX requests
    event.detail.parameters['page-num'] = pageNum;
    event.detail.parameters['book-id'] = bookId;
    event.detail.parameters['top-word'] = topWord;
});

document.addEventListener('DOMContentLoaded', function() {
    loadPage(pageNum).then(() => {
        log('Page loaded successfully.');
        renderWordsContainer(0);
    }).catch(error => {
        console.error('Failed to load page:', error);
    });
});
