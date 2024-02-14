import {log, getElement} from './utils';

export class Viewport {
    static pageBookScrollerId = 'book-page-scroller';
    static wordsContainerId = 'words-container';
    static topNavbarId = 'top-navbar';

    bookId: string;
    pageNum: number;
    totalWords: number = 0;

    wordsContainer: HTMLElement;
    bookPageScroller: HTMLElement;
    wordsContainerTopMargin: number;

    topWord: number = 0; // the first visible word index
    lineHeight: number = 0; // average line height


    constructor() {
        this.wordsContainer = this.getWordsContainer();
        this.bookPageScroller = this.getBookPageScroller();
        this.wordsContainerTopMargin = getElement(Viewport.topNavbarId).getBoundingClientRect().height;
        this.bookId = document.body.getAttribute('data-book-id') || '';
        this.pageNum = parseInt(document.body.getAttribute('data-book-page-number') || '0');
    }

    public getWordsContainer(): HTMLElement {
        return getElement(Viewport.wordsContainerId);
    }

    public getWordsContainerHeight(): number {
        return this.wordsContainer.getBoundingClientRect().height;
    }

    public getTopNavbar(): HTMLElement {
        return getElement(Viewport.topNavbarId);
    }

    public getBookPageScroller(): HTMLElement {
        return getElement(Viewport.pageBookScrollerId);
    }

    public calculateTotalWords(): number {
        // Calculate the number of words by counting word elements within the wordsContainer
        const wordElements = this.wordsContainer.querySelectorAll('.word');
        return  wordElements.length;
    }

    public word(index: number): HTMLElement {
        const result = document.getElementById(`word-${index}`);
        if (!result) {
            throw new Error(`Could not find word ${index}.`);
        }
        return result as HTMLElement;
    }

    public domChanged(): void {
        this.wordsContainer = this.getWordsContainer();
        this.bookPageScroller = this.getBookPageScroller();
        this.wordsContainerTopMargin = this.getTopNavbar().getBoundingClientRect().height;
        this.totalWords = this.calculateTotalWords();
        console.log('domChanged: bookId:', this.bookId, 'pageNum:', this.pageNum, 'totalWords:', this.totalWords, 'wordsContainerHeight:', this.getWordsContainerHeight());
    }

    public getWordTop(wordId: number = 0): number {
        // find targetLastWord top coordinate
        const word = document.getElementById('word-' + wordId);
        return word ? word.getBoundingClientRect().top - this.wordsContainerTopMargin : 0;
    }

    public loadPage(pageNumber: number, topWord: number | undefined = 0): Promise<void> {
        // if topWord is undefined you should call reportReadingPosition() by yourself
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
                    if (!bookElement) {
                        throw new Error('Book element not found');
                    }
                    bookElement.innerHTML = data.html;
                    this.domChanged();

                    this.bookId = data.data.bookId;
                    this.pageNum = parseInt(data.data.pageNum);
                    this.totalWords = this.calculateTotalWords();
                    log(`Total words: ${this.totalWords}, topWord: ${topWord}`);

                    if (topWord != undefined) {
                        this.topWord = topWord;
                        if (topWord > 0) {
                            this.bookPageScroller.scrollTop = this.getWordTop(topWord);
                            log('scrollTop:', this.bookPageScroller.scrollTop);
                        } else {
                            this.bookPageScroller.scrollTop = 0;
                        }
                        this.reportReadingLocation();
                    }

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
        const containerBottom = this.bookPageScroller.getBoundingClientRect().bottom;
        const containerTop = this.wordsContainerTopMargin;
        log('Searching for visible word between', low, high, 'container rect:', containerTop, containerBottom);

        while (low < high) {
            let mid = Math.floor((low + high) / 2);
            let word = this.word(mid);
            if (!word) {
                log('logical error: word not found:', mid);
                return low;
            }
            let rect = word.getBoundingClientRect();
            totalHeight.value += rect.height;
            wordCount.value++;
            log('low:', low, 'high:', high, 'mid:', mid, 'rect:', rect.top, rect.bottom);

            if ((rect.top >= containerTop) && (rect.bottom <= containerBottom)) {
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
        let high = this.binarySearchVisibleWord(0, this.totalWords, totalHeight, wordCount);
        log('found high bound:', high);
        let low = 0;
        const containerHeight = this.getWordsContainerHeight();
        const containerTop = this.wordsContainerTopMargin;
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

    public reportReadingLocation(): void {
        // Determine the first visible word and report to the server the reading location
        let url = `/location?top-word=${this.getFirstVisibleWord()}&book-id=${this.bookId}&book-page-num=${this.pageNum}`;
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
        if (this.bookPageScroller.scrollTop === 0) {
            if (this.pageNum === 1) {
                return;
            }
            await this.loadPage(this.pageNum - 1, undefined);
            // Scroll to the bottom of the page
            this.bookPageScroller.scrollTop = this.getWordsContainerHeight() - this.bookPageScroller.clientHeight;
            this.reportReadingLocation();
        } else {
            // no need to check for negative scroll top, it will be handled by the browser
            log('***** scrollTop:', this.bookPageScroller.scrollTop, 'clientHeight-lineHeight:', this.bookPageScroller.clientHeight - this.lineHeight);
            this.bookPageScroller.scrollTop -= this.bookPageScroller.clientHeight - this.lineHeight;
            this.reportReadingLocation();
        }
    }

    public async scrollDown(): Promise<void> {
        // Scroll one viewport down
        if (this.word(this.totalWords - 1).getBoundingClientRect().bottom <= this.bookPageScroller.getBoundingClientRect().bottom) {
            await this.loadPage(this.pageNum + 1, 0);
        } else {
            // no need to check for too large scroll top, it will be handled by the browser
            this.bookPageScroller.scrollTop += this.bookPageScroller.clientHeight - this.lineHeight;
            log('***** scrollTop:', this.bookPageScroller.scrollTop, 'clientHeight,lineHeight:', this.bookPageScroller.clientHeight, this.lineHeight);
            this.reportReadingLocation();
        }
    }
}

// Global instance of the Viewport class
export const viewport = new Viewport();
