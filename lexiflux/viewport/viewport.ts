import { log, suppressRedraw, resumeRedraw } from './utils';

const pageBookScrollerId = 'book-page-scroller';
const wordsContainerId = 'words-container';
const topNavbarId = 'top-navbar';

export let bookId: string = '';
export let pageNum: number = 0;


let wordsContainer = getWordsContainer()
let pageScroller = getBookPageScroller();

let wordSpans: HTMLElement[] = [];  // todo: we do not need wordSpans, just max word ID
let totalWords: number = 0;

let topWord: number = 0;
let lastTopWord: number | undefined;

export function getWordsContainer(): HTMLElement {
    const container = document.getElementById(wordsContainerId);
    if (!container) {
        throw new Error(`Failed to find the words container (id=${wordsContainerId}).`);
    }
    return container as HTMLElement;
}

export function getTopNavbar(): HTMLElement {
    const container = document.getElementById(topNavbarId);
    if (!container) {
        throw new Error(`Failed to find the top navbar (id=${topNavbarId}).`);
    }
    return container as HTMLElement;
}

export function getBookPageScroller(): HTMLElement {
    const pageScroller = document.getElementById(pageBookScrollerId);
    if (!pageScroller) {
        throw new Error(`Could not find page scroller (id=${pageBookScrollerId}).`);
    }
    return pageScroller as HTMLElement;
}

export function initializeVariables(): void {
    bookId = document.body.getAttribute('data-book-id') || '';
    pageNum = parseInt(document.body.getAttribute('data-page-number') || '0');
    console.log('bookId:', bookId, 'pageNum:', pageNum);
}

export function findViewport(targetLastWord?: number): number {
  // find targetLastWord top coordinate
  const word = document.getElementById('word-' + targetLastWord);
    if (!word) {
        return 0;
    }
  return word.getBoundingClientRect().top - getTopNavbar().getBoundingClientRect().height;
}

export function fillWordsContainer(startWordIndex: number): void {
    topWord = startWordIndex;
    lastTopWord = topWord;

    wordsContainer.innerHTML = '';
    for (let i = 0; i < wordSpans.length; i++) {
        wordsContainer.appendChild(wordSpans[i]);
    }
    if (startWordIndex > 0) {
        getBookPageScroller().scrollTop = findViewport(startWordIndex);
        console.log('scrollTop:', getBookPageScroller().scrollTop);
    } else {
        getBookPageScroller().scrollTop = 0;
    }
}

export function loadPage(pageNumber: number, topWord: number = 0): Promise<void> {
    return new Promise((resolve, reject) => {
        fetch('/page?book-id=' + bookId + '&page-num=' + pageNumber)
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
                log('Page ', pageNumber, 'topWord', topWord, ' loaded successfully.');

                const bookElement = document.getElementById('book');
                if (bookElement) {
                    bookElement.innerHTML = data.html;
                }

                wordsContainer = getWordsContainer()
                totalWords = data.data.words.length;
                lastTopWord = undefined;
                pageNum = parseInt(data.data.pageNum);
                bookId = data.data.bookId;

                let wordCounter = 0;

                wordSpans = data.data.words.map((word: string) => {
                    let wordElement;
                    if (word === '<br/>') {
                        wordElement = document.createElement('br');
                    } else {
                        wordElement = document.createElement('span');
                        wordElement.id = 'word-' + wordCounter; // Use the separate counter
                        wordElement.className = 'word';
                        wordElement.innerHTML = ' ' + word;
                        wordCounter++; // Increment only when a word is processed
                    }
                    return wordElement;
                });

                fillWordsContainer(topWord);
                resolve();
            })
            .catch(error => {
                console.error('Error:', error);
                reject(error);
            });
    });
}

function binarySearchVisibleWord(low: number, high: number): number {
    // Look for any visible word in the container - first that we find
    const containerHeight = wordsContainer.getBoundingClientRect().height;
    const containerTop = getTopNavbar().getBoundingClientRect().height;
    log('Searching for visible word between', low, high, 'container rect:', containerTop, containerHeight);

    while (low < high) {
        let mid = Math.floor((low + high) / 2);
        let word = document.getElementById('word-' + mid);
        if (!word) {
            log('logical error: word not found:', mid);
            return low;
        }
        let rect = word.getBoundingClientRect();
        log('low:', low, 'high:', high, 'mid:', mid, 'rect:', rect.top, rect.bottom);

        if ((rect.top >= containerTop) && (rect.bottom <= containerHeight)) {
            return mid;
        }
        if (rect.top < containerTop) {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    console.log('return low:', low);
    return low;
}

export function getFistVisibleWord(): number {
    // Look for the first visible word in the container
    log('Searching for the first visible word');

    // first find any visible word - this is the upper bound in search for the first visible word
    let high = binarySearchVisibleWord(0, wordSpans.length);
    console.log('found high bound:', high);
    let low = 0;
    const containerHeight = wordsContainer.getBoundingClientRect().height;
    const containerTop = getTopNavbar().getBoundingClientRect().height;
    console.log('container:', containerTop, containerHeight);

    // look for first visible word using binary search
    while (low < high) {
        let mid = Math.floor((low + high) / 2);
        let word = document.getElementById('word-' + mid);
        if (!word) {
            log('logical error: word not found:', mid);
            return low;
        }
        let rect = word.getBoundingClientRect();
        log('low:', low, 'high:', high, 'mid:', mid, 'top:', rect.top);

        if (rect.top < containerTop) {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    console.log('return low:', low);
    return low;
}

export function reportReadingPosition(): void {
    let url = `/position?top-word=${topWord}&book-id=${bookId}&page-num=${pageNum}`;
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

export function setTopWord(newTopWord: number) {
    topWord = newTopWord;
}

export function getTotalWords(): number {
    return totalWords;
}

export function getWordSpans(): HTMLElement[] {
    return wordSpans;
}
