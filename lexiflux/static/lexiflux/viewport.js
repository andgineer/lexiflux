let bookId = document.body.getAttribute('data-book-id');
let pageNum = document.body.getAttribute('data-page-number');
let clickWordUrl = document.body.getAttribute('click-word-url');

let wordSpans;
let totalWords;

let topWord;
let lastTopWord;
let lastAddedWordIndex;
let resizeTimeout;

function wordsInViewport() {
    // Count the number of words that fit in the viewport
    let containerRect = wordsContainer.getBoundingClientRect();
    let lastVisibleWordIndex = lastAddedWordIndex;
    let visibleWordsNum = lastVisibleWordIndex - topWord + 1;
    log('Visible words:', visibleWordsNum);
    let lastWordElement = document.getElementById('word-' + lastVisibleWordIndex);

    let bottomGapInLines;
    if (lastWordElement) {
        let lastWordRect = lastWordElement.getBoundingClientRect();
        let lineHeight = lastWordRect.height;
        let spaceAtBottom = containerRect.bottom - lastWordRect.bottom;
        bottomGapInLines = spaceAtBottom / lineHeight;
        log('bottomGapInLines:', bottomGapInLines)
    }
    if (!lastWordElement || bottomGapInLines > 1.5) {
        renderWordsContainer(0);
        lastVisibleWordIndex = lastAddedWordIndex;
        visibleWordsNum = lastVisibleWordIndex + 1;
        renderWordsContainer(topWord);
        log('Visible words after re-fill:', visibleWordsNum);
    }
    return visibleWordsNum === 0 ? 1 : visibleWordsNum;
}

function findViewport(targetLastWord) {
    // Search for the such topWord so the last visible word is the targetLastWord.
    // targetLastWord defaults to the word before the current topWord.
    if (targetLastWord === undefined) {
        targetLastWord = topWord - 1;
    }
    let high = targetLastWord - 1;  // topWord changed by renderWordsContainer so fix it there
    suppressRedraw(wordsContainer);
    try {
        // heuristic to narrow down the search: go back by 2 viewports number of words
        let low = Math.max(0, topWord - wordsInViewport() * 2);
        renderWordsContainer(low);
        let lastVisibleWord = lastAddedWordIndex;
        if (lastVisibleWord === targetLastWord) {
            return low; // wild guess was correct
        }
        else if (lastVisibleWord > targetLastWord) {
            // If the last visible word is inside the viewport
            // we should shift the viewport to the left and let the binary search do the rest
            low = 0;
        }
        let viewportTopWord = binarySearchForTopWord(low, high, targetLastWord);
        renderWordsContainer(viewportTopWord);
        if (lastAddedWordIndex === targetLastWord) {
            log('try squeeze more words in the viewport');
            for (let i = viewportTopWord; i >= 0; i--) {
                renderWordsContainer(i);
                if (lastAddedWordIndex === targetLastWord) {
                    viewportTopWord = i;
                } else {
                    renderWordsContainer(viewportTopWord);
                    break;
                }
            }
            return viewportTopWord;
        }
        else {
            // If the search did not find the exact match, it couldn't be exactly the last
            log('shift viewport till the target is visible');
            for (let i = viewportTopWord; i >= 0; i--) {
                renderWordsContainer(i);
                if (lastAddedWordIndex >= targetLastWord) {
                    viewportTopWord = i;
                } else {
                    renderWordsContainer(viewportTopWord);
                    break;
                }
            }
            return viewportTopWord;
        }
    } finally {
        resumeRedraw(wordsContainer);
    }
}

function binarySearchForTopWord(low, high, targetLastWord) {
    log('Searching for topWord:', targetLastWord, `between`, low, high);
    while (low < high) {
        let mid = Math.floor((low + high) / 2);
        suppressRedraw(wordsContainer);
        renderWordsContainer(mid);
        resumeRedraw(wordsContainer);

        let lastVisibleWord = lastAddedWordIndex;
        log('mid:', mid, 'lastVisibleWord:', lastVisibleWord, 'low:', low, 'high:', high);

        if (lastVisibleWord < targetLastWord) {
            low = mid + 1;
        } else if (lastVisibleWord >= targetLastWord) {
            high = mid;
        }
    }
    return low;
}

function renderWordsContainer(newTopWord) {
    suppressRedraw(wordsContainer);
    try {
        if (newTopWord === undefined) {
            newTopWord = topWord;
        }
        if (lastTopWord !== newTopWord) {
            fillWordsContainer(newTopWord);
        } else {
            resizeWordsContainer();
        }
    } finally {
        resumeRedraw(wordsContainer);
    }
}

function fillWordsContainer(startWordIndex) {
    topWord = startWordIndex;
    lastTopWord = topWord;
    let containerRect = wordsContainer.getBoundingClientRect();

    wordsContainer.innerHTML = ''; // Clear the container

    for (let i = startWordIndex; i < wordSpans.length; i++) {
        wordsContainer.appendChild(wordSpans[i]);
        let wordRect = wordSpans[i].getBoundingClientRect();
        if (wordRect.bottom > containerRect.bottom) {
            // Word does not fully fit, remove it
            wordsContainer.removeChild(wordSpans[i]);
            break;
        }
        lastAddedWordIndex = i; // Update last added word index
    }
    log('fillWordsContainer from', startWordIndex, 'lastAddedWordIndex:', lastAddedWordIndex);
    htmx.process(wordsContainer);
}

function resizeWordsContainer() {
    let containerRect = wordsContainer.getBoundingClientRect();
    let oldLastAddedWordIndex = lastAddedWordIndex;

    // Check if the last word in the container is visible
    let lastWordRect = wordSpans[lastAddedWordIndex].getBoundingClientRect();
    if (lastWordRect.bottom <= containerRect.bottom) {
        // Add words if the last word is fully visible
        for (let i = lastAddedWordIndex + 1; i < wordSpans.length; i++) {
            wordsContainer.appendChild(wordSpans[i]);
            let wordRect = wordSpans[i].getBoundingClientRect();
            if (wordRect.bottom > containerRect.bottom) {
                wordsContainer.removeChild(wordSpans[i]);
                break;
            }
            lastAddedWordIndex = i;
        }
    } else {
        // Remove words if the last word is not fully visible
        while (lastAddedWordIndex > topWord) {
            let wordRect = wordSpans[lastAddedWordIndex].getBoundingClientRect();
            if (wordRect.bottom > containerRect.bottom) {
                wordsContainer.removeChild(wordSpans[lastAddedWordIndex]);
                lastAddedWordIndex--;
            } else {
                break;
            }
        }
    }
    if (oldLastAddedWordIndex !== lastAddedWordIndex) {
        log('resizeWordsContainer', lastAddedWordIndex - oldLastAddedWordIndex);
        htmx.process(wordsContainer);
    }
}

function loadPage(pageNumber) {
    return new Promise((resolve, reject) => {
        fetch('/page?page-num=' + pageNumber)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json(); // Parse the JSON response
            })
            .then(data => {
                document.getElementById('book').innerHTML = data.html;
                // Update global variables with new data
                if (data.data) {
                    totalWords = data.data.words.length;
                    lastTopWord = undefined;
                    pageNum = parseInt(data.data.pageNum);
                    bookId = data.data.bookId;

                    wordSpans = data.data.words.map((word, index) => {
                        let wordSpan = document.createElement('span');
                        wordSpan.id = 'word-' + index;
                        wordSpan.className = 'word';
                        wordSpan.setAttribute('hx-trigger', 'click');
                        wordSpan.setAttribute('hx-get', clickWordUrl + '?id=' + index);
                        wordSpan.setAttribute('hx-swap', 'outerHTML');
                        wordSpan.textContent = word;
                        return wordSpan;
                    });
                    reInitDom();
                    resolve(); // Resolve the promise after updating the DOM
                } else {
                    console.error('Invalid or missing data in response');
                    log("Response data:", data);
                    reject(new Error('Invalid or missing data in response'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                reject(error); // Reject the promise in case of an error
            });
    });
}

function reportVieportChange() {
    let url = `/viewport?top-word=${topWord}&book-id=${bookId}&page-num=${pageNum}`;
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            // No need to process the server's response
        })
        .catch(error => console.error('Error:', error));
}
