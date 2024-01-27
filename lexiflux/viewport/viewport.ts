import { log, suppressRedraw, resumeRedraw } from './utils';

const pageBookScrollerId = 'book-page-scroller';
const wordsContainerId = 'words-container';

export let bookId: string = '';
export let pageNum: number = 0;


let wordsContainer = getWordsContainer()

let wordSpans: HTMLElement[] = [];  // todo: we do not need wordSpans, just max word ID
let totalWords: number = 0;

let topWord: number = 0;
let lastTopWord: number | undefined;

export function getWordsContainer(): HTMLElement {
    const container = document.getElementById(wordsContainerId);
    if (!container) {
        throw new Error(`Failed to find the words-container (id=${wordsContainerId}).`);
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
  return word.getBoundingClientRect().top;
}

export function fillWordsContainer(startWordIndex: number): void {
    topWord = startWordIndex;
    lastTopWord = topWord;

    wordsContainer.innerHTML = '';
    for (let i = 0; i < wordSpans.length; i++) {
        wordsContainer.appendChild(wordSpans[i]);
    }

    getBookPageScroller().scrollTop = findViewport(startWordIndex);
}

export function loadPage(pageNumber: number): Promise<void> {
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
                log('Page ', pageNumber, ' loaded successfully.');

                const bookElement = document.getElementById('book');
                if (bookElement) {
                    bookElement.innerHTML = data.html;
                }

                wordsContainer = getWordsContainer()
                totalWords = data.data.words.length;
                lastTopWord = undefined;
                pageNum = parseInt(data.data.pageNum);
                bookId = data.data.bookId;

                wordSpans = data.data.words.map((word: string, index: number) => {
                    let wordElement;
                    if (word === '<br/>') {
                        wordElement = document.createElement('br');
                    } else {
                        wordElement = document.createElement('span');
                        wordElement.id = 'word-' + index;
                        wordElement.className = 'word';
                        wordElement.innerHTML = ' ' + word;
                    }
                    return wordElement;
                });

                resolve();
            })
            .catch(error => {
                console.error('Error:', error);
                reject(error);
            });
    });
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

export function getTotalWords(): number {
    return totalWords;
}

export function getWordSpans(): HTMLElement[] {
    return wordSpans;
}
