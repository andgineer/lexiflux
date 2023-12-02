import { log, suppressRedraw, resumeRedraw } from './utils';
declare const htmx: any;  // included in the HTML page

export let bookId: string = '';
export let pageNum: number = 0;
export let clickWordUrl: string = '';

let wordsContainer = initializeWordsContainer()

let wordSpans: HTMLElement[] = [];
let totalWords: number = 0;

let topWord: number = 0;
let lastTopWord: number | undefined;
let lastAddedWordIndex: number = 0;

function initializeWordsContainer(): HTMLElement {
    const container = document.getElementById('words-container');
    if (!container) {
        throw new Error("Failed to find the 'words-container' element.");
    }
    return container as HTMLElement;
}

export function initializeVariables(): void {
    bookId = document.body.getAttribute('data-book-id') || '';
    pageNum = parseInt(document.body.getAttribute('data-page-number') || '0');
    clickWordUrl = document.body.getAttribute('data-click-word-url') || '';
    console.log('bookId:', bookId, 'pageNum:', pageNum, 'clickWordUrl:', clickWordUrl);
}

export function wordsInViewport(): number {
    let containerRect = wordsContainer.getBoundingClientRect();
    let lastVisibleWordIndex = lastAddedWordIndex;
    let visibleWordsNum = lastVisibleWordIndex - topWord + 1;
    log('Visible words:', visibleWordsNum);

    let lastWordElement = document.getElementById('word-' + lastVisibleWordIndex);
    let bottomGapInLines: number = 0;

    if (lastWordElement) {
        let lastWordRect = lastWordElement.getBoundingClientRect();
        let lineHeight = lastWordRect.height;
        let spaceAtBottom = containerRect.bottom - lastWordRect.bottom;
        bottomGapInLines = spaceAtBottom / lineHeight;
        log('bottomGapInLines:', bottomGapInLines);
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

export function findViewport(targetLastWord?: number): number | undefined {
    targetLastWord = targetLastWord === undefined ? topWord - 1 : targetLastWord;
    let high = targetLastWord - 1;
    suppressRedraw(wordsContainer);

    try {
        let low = Math.max(0, topWord - wordsInViewport() * 2);
        renderWordsContainer(low);
        let lastVisibleWord = lastAddedWordIndex;

        if (lastVisibleWord === targetLastWord) {
            return low;
        } else if (lastVisibleWord > targetLastWord) {
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
                    return viewportTopWord;
                }
            }
        } else {
            log('shift viewport till the target is visible');
            for (let i = viewportTopWord; i >= 0; i--) {
                renderWordsContainer(i);
                if (lastAddedWordIndex >= targetLastWord) {
                    viewportTopWord = i;
                } else {
                    renderWordsContainer(viewportTopWord);
                    return viewportTopWord;
                }
            }
        }
    } finally {
        resumeRedraw(wordsContainer);
    }
}

export function binarySearchForTopWord(low: number, high: number, targetLastWord: number): number {
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

export function renderWordsContainer(newTopWord?: number): void {
    suppressRedraw(wordsContainer);

    try {
        newTopWord = newTopWord === undefined ? topWord : newTopWord;
        if (lastTopWord !== newTopWord) {
            fillWordsContainer(newTopWord);
        } else {
            resizeWordsContainer();
        }
    } finally {
        resumeRedraw(wordsContainer);
    }
}

export function fillWordsContainer(startWordIndex: number): void {
    topWord = startWordIndex;
    lastTopWord = topWord;
    let containerRect = wordsContainer.getBoundingClientRect();

    wordsContainer.innerHTML = '';

    for (let i = startWordIndex; i < wordSpans.length; i++) {
        wordsContainer.appendChild(wordSpans[i]);
        let wordRect = wordSpans[i].getBoundingClientRect();
        if (wordRect.bottom > containerRect.bottom) {
            wordsContainer.removeChild(wordSpans[i]);
            break;
        }
        lastAddedWordIndex = i;
    }
    log('fillWordsContainer from', startWordIndex, 'lastAddedWordIndex:', lastAddedWordIndex);
    htmx.process(wordsContainer);
}

export function resizeWordsContainer(): void {
    let containerRect = wordsContainer.getBoundingClientRect();
    let oldLastAddedWordIndex = lastAddedWordIndex;

    let lastWordRect = wordSpans[lastAddedWordIndex]?.getBoundingClientRect();
    if (lastWordRect && lastWordRect.bottom <= containerRect.bottom) {
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
        while (lastAddedWordIndex > topWord) {
            let wordRect = wordSpans[lastAddedWordIndex]?.getBoundingClientRect();
            if (wordRect && wordRect.bottom > containerRect.bottom) {
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

export function loadPage(pageNumber: number): Promise<void> {
    return new Promise((resolve, reject) => {
        fetch('/page?page-num=' + pageNumber)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (!data || !data.data) {
                    throw new Error('Invalid or missing data in response');
                }

                const bookElement = document.getElementById('book');
                if (bookElement) {
                    bookElement.innerHTML = data.html;
                }

                wordsContainer = initializeWordsContainer()
                totalWords = data.data.words.length;
                lastTopWord = undefined;
                pageNum = parseInt(data.data.pageNum);
                bookId = data.data.bookId;

                wordSpans = data.data.words.map((word: string, index: number) => {
                    let wordSpan = document.createElement('span');
                    wordSpan.id = 'word-' + index;
                    wordSpan.className = 'word';
                    wordSpan.setAttribute('hx-trigger', 'click');
                    wordSpan.setAttribute('hx-get', clickWordUrl + '?id=' + index);
                    wordSpan.setAttribute('hx-swap', 'outerHTML');
                    wordSpan.textContent = word;
                    return wordSpan;
                });

                resolve();
            })
            .catch(error => {
                console.error('Error:', error);
                reject(error);
            });
    });
}

export function reportVieportChange(): void {
    let url = `/viewport?top-word=${topWord}&book-id=${bookId}&page-num=${pageNum}`;
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            // Process response if necessary
        })
        .catch(error => console.error('Error:', error));
}

export function getBookId(): string {
    return bookId;
}

export function getPageNum(): number {
    return pageNum;
}

export function getTopWord(): number {
    return topWord;
}

export function getTotalWords(): number {
    return totalWords;
}

export function getLastAddedWordIndex(): number {
    return lastAddedWordIndex;
}
