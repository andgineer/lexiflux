import {log} from './utils';

export class Viewport {
    static pageBookScrollerId = 'book-page-scroller';
    static wordsContainerId = 'words-container';
    static topNavbarId = 'top-navbar';

    bookId: string = '';
    pageNum: number = 0;
    totalWords: number = 0;
    wordSpans: HTMLElement[] = [];

    wordsContainer: HTMLElement;

    topWord: number = 0; // the first visible word index
    lineHeight: number = 0; // average line height


    constructor() {
        this.wordsContainer = this.getWordsContainer();
    }

    public getWordsContainer(): HTMLElement {
        const container = document.getElementById(Viewport.wordsContainerId);
        if (!container) {
            throw new Error(`Failed to find the words container (id=${Viewport.wordsContainerId}).`);
        }
        return container as HTMLElement;
    }

    public getTopNavbar(): HTMLElement {
        const container = document.getElementById(Viewport.topNavbarId);
        if (!container) {
            throw new Error(`Failed to find the top navbar (id=${Viewport.topNavbarId}).`);
        }
        return container as HTMLElement;
    }

    public getBookPageScroller(): HTMLElement {
        const pageScroller = document.getElementById(Viewport.pageBookScrollerId);
        if (!pageScroller) {
            throw new Error(`Could not find page scroller (id=${Viewport.pageBookScrollerId}).`);
        }
        return pageScroller as HTMLElement;
    }

    public initializeVariables(): void {
        this.bookId = document.body.getAttribute('data-book-id') || '';
        this.pageNum = parseInt(document.body.getAttribute('data-book-page-number') || '0');
        this.wordsContainer = this.getWordsContainer();
        console.log('bookId:', this.bookId, 'pageNum:', this.pageNum);
    }

    public getWordTop(wordId: number = 0): number {
        // find targetLastWord top coordinate
        const word = document.getElementById('word-' + wordId);
        return word ? word.getBoundingClientRect().top - this.getTopNavbar().getBoundingClientRect().height : 0;
    }

    public fillWordsContainer(startWordIndex: number): void {
        // Fill the words container with the words from wordSpans.
        // Set the scrollTop to the top of the word with startWordIndex if it is not 0, otherwise set it to 0.
        this.wordsContainer.innerHTML = '';
        for (let i = 0; i < this.wordSpans.length; i++) {
            this.wordsContainer.appendChild(this.wordSpans[i]);
        }
        if (startWordIndex > 0) {
            this.getBookPageScroller().scrollTop = this.getWordTop(startWordIndex);
            console.log('scrollTop:', this.getBookPageScroller().scrollTop);
        } else {
            this.getBookPageScroller().scrollTop = 0;
        }
    }

    public loadPage(pageNumber: number, topWord: number = 0): Promise<void> {
        return new Promise((resolve, reject) => {
            fetch('/page?book-id=' + this.bookId + '&book-page-num=' + pageNumber + '&top-word=' + topWord)
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

                    this.wordsContainer = this.getWordsContainer();
                    this.totalWords = data.data.words.length;
                    this.pageNum = parseInt(data.data.pageNum);
                    this.bookId = data.data.bookId;

                    let wordCounter = 0;

                    this.wordSpans = data.data.words.map((word: string) => {
                        let wordElement;
                        if (word === '<br/>') {
                            wordElement = document.createElement('br');
                        } else {
                            wordElement = document.createElement('span');
                            wordElement.id = 'word-' + wordCounter;
                            wordElement.className = 'word';
                            wordElement.innerHTML = ' ' + word;
                            wordCounter++;
                        }
                        return wordElement;
                    });

                    this.fillWordsContainer(topWord);
                    resolve();
                })
                .catch(error => {
                    console.error('Error:', error);
                    reject(error);
                });
        });
    }

    private binarySearchVisibleWord(
        low: number,
        high: number,
        totalHeight: {value: number},
        wordCount: {value: number}
    ): number {
        // Look for any visible word in the container - first that we find
        const containerHeight = this.wordsContainer.getBoundingClientRect().height;
        const containerTop = this.getTopNavbar().getBoundingClientRect().height;
        log('Searching for visible word between', low, high, 'container rect:', containerTop, containerHeight);

        while (low < high) {
            let mid = Math.floor((low + high) / 2);
            let word = document.getElementById('word-' + mid);
            if (!word) {
                log('logical error: word not found:', mid);
                return low;
            }
            let rect = word.getBoundingClientRect();
            totalHeight.value += rect.height;
            wordCount.value++;
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
        log('return low:', low);
        return low;
    }

    public getFirstVisibleWord(): number {
        // Look for the first visible word in the container
        log('Searching for the first visible word');

        // first find any visible word - this is the upper bound in search for the first visible word
        let totalHeight = {value: 0};  // accumulate statistics to
        let wordCount = {value: 0};    // calculate average line height
        let high = this.binarySearchVisibleWord(0, this.wordSpans.length, totalHeight, wordCount);
        log('found high bound:', high);
        let low = 0;
        const containerHeight = this.wordsContainer.getBoundingClientRect().height;
        const containerTop = this.getTopNavbar().getBoundingClientRect().height;
        log('container:', containerTop, containerHeight);

        // look for first visible word using binary search
        while (low < high) {
            let mid = Math.floor((low + high) / 2);
            let word = document.getElementById('word-' + mid);
            if (!word) {
                log('logical error: word not found:', mid);
                return low;
            }
            let rect = word.getBoundingClientRect();
            totalHeight.value += rect.height;
            wordCount.value++;
            log('low:', low, 'high:', high, 'mid:', mid, 'top:', rect.top);

            if (rect.top < containerTop) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
         // Calculate and save the average line height
        // todo: clear from spikes
        if (wordCount.value > 0) {
            this.lineHeight = totalHeight.value / wordCount.value;
        }
        log('return low:', low);
        return low;
    }

    public reportReadingPosition(): void {
        // Determine the first visible word and report to the server the reading position
        let url = `/position?top-word=${this.getFirstVisibleWord()}&book-id=${this.bookId}&book-page-num=${this.pageNum}`;
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
    
    public async scrollUp(): Promise<void> {
        // Scroll one viewport up
        if (this.getBookPageScroller().scrollTop === 0) {
            if (this.pageNum === 1) {
                return;
            }
            await this.loadPage(this.pageNum - 1, 0);
            this.getBookPageScroller().scrollTop = this.wordsContainer.getBoundingClientRect().height - this.getBookPageScroller().clientHeight;
            this.reportReadingPosition();
        } else {
            // no need to check for negative scroll top, it will be handled by the browser
            log('***** scrollTop:', this.getBookPageScroller().scrollTop, 'clientHeight-lineHeight:', this.getBookPageScroller().clientHeight - this.lineHeight);
            this.getBookPageScroller().scrollTop -= this.getBookPageScroller().clientHeight - this.lineHeight;
            this.reportReadingPosition();
        }
    }

    public async scrollDown(): Promise<void> {
        // Scroll one viewport down
        if (this.wordSpans[this.wordSpans.length - 1].getBoundingClientRect().bottom <= this.getBookPageScroller().getBoundingClientRect().bottom) {
            await this.loadPage(this.pageNum + 1, 0);
            this.reportReadingPosition();
        } else {
            // no need to check for too large scroll top, it will be handled by the browser
            this.getBookPageScroller().scrollTop += this.getBookPageScroller().clientHeight - this.lineHeight;
            log('***** scrollTop:', this.getBookPageScroller().scrollTop, 'clientHeight,lineHeight:', this.getBookPageScroller().clientHeight, this.lineHeight);
            this.reportReadingPosition();
        }
    }
}


// Global instance of the Viewport class
export const viewport = new Viewport();
