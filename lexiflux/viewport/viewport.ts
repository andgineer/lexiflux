import { log, getElement, closeModal } from './utils';
import { clearLexicalPanel } from './translate';
import { spanManager } from './TranslationSpanManager';

export class Viewport {
    static pageBookScrollerId = 'book-page-scroller';
    static wordsContainerId = 'words-container';
    static topNavbarId = 'top-navbar';
    static totalPagesId = 'total-pages';
    static progressBarId = 'progress-bar';
    static pageNumberId = 'page-number';
    static goToPageModalId = 'goToPageModal';
    static maxPageNumberId = 'maxPageNumber';
    static emptySpaceId = 'empty-space';

    bookCode: string;
    pageNumber: number;
    totalPages: number;
    totalWords: number = 0;

    wordsContainer: HTMLElement;
    bookPageScroller: HTMLElement;
    wordsContainerTopMargin: number;

    progressBar: HTMLElement;
    pageNumberElement: HTMLElement;
    totalPagesElement: HTMLElement;
    goToPageModal: HTMLElement;
    emptySpace: HTMLElement;

    topWord: number = 0; // the first visible word index
    lineHeight: number = 0; // average line height

    constructor() {
        this.wordsContainer = this.getWordsContainer();
        this.bookPageScroller = this.getBookPageScroller();
        this.wordsContainerTopMargin = getElement(Viewport.topNavbarId).getBoundingClientRect().height;
        this.bookCode = document.body.getAttribute('data-book-code') || '';
        this.pageNumber = parseInt(document.body.getAttribute('data-book-page-number') || '0');
        this.totalPages = this.parseTotalPages();

        this.progressBar = getElement(Viewport.progressBarId);
        this.pageNumberElement = getElement(Viewport.pageNumberId);
        this.totalPagesElement = getElement(Viewport.totalPagesId);

        this.goToPageModal = getElement(Viewport.goToPageModalId);

        this.emptySpace = getElement(Viewport.emptySpaceId);

        (window as any).handleLinkClick = this.handleLinkClick.bind(this);
        this.updateReadingProgress()
        log(`Viewport constructor: bookCode: ${this.bookCode}, pageNumber: ${this.pageNumber}`);
    }  // constructor

    private adjustEmptySpace(): void {
        this.emptySpace.style.height = `${window.innerHeight}px`;
    }

    private parseTotalPages(): number {
        const totalPagesAttr = document.body.getAttribute('data-total-pages');
        if (totalPagesAttr === null) {
            console.error('data-total-pages attribute is missing from the body element');
            return 0;
        }
        const parsed = parseInt(totalPagesAttr, 10);
        if (isNaN(parsed)) {
            console.error(`Invalid data-total-pages value: "${totalPagesAttr}"`);
            return 0;
        }
        return parsed;
    }

    public getWordsContainer(): HTMLElement {
        return getElement(Viewport.wordsContainerId);
    }  // getWordsContainer

    public getWordsContainerHeight(): number {
        return this.wordsContainer.getBoundingClientRect().height;
    }  // getWordsContainerHeight

    public getTopNavbar(): HTMLElement {
        return getElement(Viewport.topNavbarId);
    }  // getTopNavbar

    public getBookPageScroller(): HTMLElement {
        return getElement(Viewport.pageBookScrollerId);
    }  // getBookPageScroller

    public calculateTotalWords(): number {
        // Calculate the number of words by counting word elements within the wordsContainer
        const wordElements = this.wordsContainer.querySelectorAll('.word');
        return wordElements.length;
    }  // calculateTotalWords

    public word(index: number): HTMLElement | null {
        return document.getElementById(`word-${index}`);
    }  // word

    public domChanged(): void {
        this.wordsContainer = this.getWordsContainer();
        this.bookPageScroller = this.getBookPageScroller();
        this.wordsContainerTopMargin = this.getTopNavbar().getBoundingClientRect().height;
        this.totalWords = this.calculateTotalWords();
        spanManager.clear();
        log('domChanged. bookCode:', this.bookCode, 'pageNum:', this.pageNumber, 'totalWords:', this.totalWords, 'wordsContainerHeight:', this.getWordsContainerHeight());
    }  // domChanged

    public scrollToWord(wordId: number): void {
        this.adjustEmptySpace();
        this.bookPageScroller.scrollTop = this.getWordTop(wordId);
    }

    public getWordTop(wordId: number = 0): number {
        // find wordId top coordinate
        const word = this.word(wordId);
        if (!word) {
          return 0;
        }
        // Get position relative to viewport
        const rect = word.getBoundingClientRect();
        // Add current scroll position to get position within scrollable container
        return rect.top + this.bookPageScroller.scrollTop - this.wordsContainerTopMargin;

    }  // getWordTop

    public loadPage(pageNumber: number, topWord: number | undefined): Promise<void> {
        // if topWord is undefined do not change bookPageScroller.scrollTop
        // if topWord is <= 0 scroll to the top of the page
        return new Promise((resolve, reject) => {
            fetch('/page?book-code=' + this.bookCode + '&book-page-number=' + pageNumber + '&top-word=' + topWord)
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

                    const bookElement = document.getElementById('words-container');
                    if (!bookElement) {
                        throw new Error('words-container element not found');
                    }
                    bookElement.innerHTML = data.html;

                    this.bookCode = data.data.bookCode;
                    this.pageNumber = parseInt(data.data.pageNumber);
                    this.updateReadingProgress();
                    clearLexicalPanel();
                    this.bookPageScroller.scrollTop = 0;  // to calculate words positions
                    this.domChanged();

                    log(`Total words: ${this.totalWords}, topWord: ${topWord}`);

                    if (topWord != undefined) {
                        this.topWord = topWord;
                        if (topWord > 0) {
                            this.scrollToWord(topWord);
                        } else {
                            this.bookPageScroller.scrollTop = 0;
                        }
                    }
                    this.addLinkClickListeners();
                    resolve();
                })
                .catch(error => {
                    console.error('Error:', error);
                    reject(error);
                });
        });
    }  // loadPage

    private binarySearchVisibleWord(
        low: number,
        high: number,
        totalHeight: {value: number},
        wordCount: {value: number}
    ): number {
        // Look for any visible word in the container - first that we find
        if (this.totalWords === 0) {
          return -1;
        }
        const containerBottom = this.bookPageScroller.getBoundingClientRect().bottom;
        const containerTop = this.wordsContainerTopMargin;
        // log('Searching for visible word between', low, high, 'container rect:', containerTop, containerBottom);

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
            // log('low:', low, 'high:', high, 'mid:', mid, 'rect:', rect.top, rect.bottom);

            if ((rect.top >= containerTop) && (rect.bottom <= containerBottom)) {
                return mid;
            }
            if (rect.top < containerTop) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        // log('return low:', low);
        return low;
    }  // binarySearchVisibleWord

    public getFirstVisibleWord(): number {
        // Look for the first visible word in the container
        log('Searching for the first visible word');
        if (this.totalWords === 0) {
          return -1;
        }

        // first find any visible word - this is the upper bound in search for the first visible word
        let totalHeight = {value: 0};  // accumulate statistics to
        let wordCount = {value: 0};    // calculate average line height
        let high = this.binarySearchVisibleWord(0, this.totalWords - 1, totalHeight, wordCount);
//         log('found high bound:', high, 'wordCount:', this.totalWords);
        let low = 0;
        const containerHeight = this.getWordsContainerHeight();
        const containerTop = this.wordsContainerTopMargin;
//         log('container:', containerTop, containerHeight);

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
//             log('low:', low, 'high:', high, 'mid:', mid, 'top:', rect.top);

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
        // log('return low:', low);
        return low;
    }  // getFirstVisibleWord

    public reportReadingLocation(): void {
        const firstVisibleWord = this.getFirstVisibleWord();
        const url = '/location';
        const data = new URLSearchParams({
            'top-word': firstVisibleWord.toString(),
            'book-code': this.bookCode,
            'book-page-number': this.pageNumber.toString(),
        });

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: data.toString()
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text();
            })
            .catch(error => console.error('Error:', error));
    }  // reportReadingLocation

    private updateReadingProgress(): void {
        // Ensure totalPages is a valid number
        if (isNaN(this.totalPages) || this.totalPages <= 0) {
            console.error('Invalid total pages:', this.totalPages);
            return;
        }

        const rawProgress = (this.pageNumber / this.totalPages) * 100;
        const progress = Math.round(Math.max(1, Math.min(rawProgress, 100)));

        // Update progress bar
        if (this.progressBar) {
            this.progressBar.setAttribute('aria-valuenow', progress.toString());
            this.progressBar.style.width = progress + '%';
        } else {
            console.error('Progress bar element not found'); // Debug log
        }

        // Update page number text
        this.pageNumberElement.textContent = this.pageNumber.toString();

        // Update total pages
        if (this.totalPagesElement) {
            this.totalPagesElement.textContent = `/ ${this.totalPages}`;
        } else {
            console.error('Total pages element not found');
        }

        // Update max page number in modal
        const maxPageNumberElement = getElement(Viewport.maxPageNumberId);
        if (maxPageNumberElement) {
            maxPageNumberElement.textContent = this.totalPages.toString();
        } else {
            console.error('Max page number element not found');
        }
    }

    private adjustTopWord(): void {
        // Shift top visible work exactly to the top of the viewport
        const firstVisibleWord = this.getFirstVisibleWord();
        if (firstVisibleWord > 0) {
            // check if prev word is partially visible
            const prevWord = this.word(firstVisibleWord - 1);
            if (prevWord) {
                const prevRect = prevWord.getBoundingClientRect();
                if (prevRect.bottom > this.wordsContainerTopMargin) {
                    log('Prev word is partially visible:', prevRect.top, prevRect.bottom, 'top:', this.wordsContainerTopMargin);
                    log('Adjusting topWord:', firstVisibleWord, 'scrollTop:', this.bookPageScroller.scrollTop, 'WordTop:', this.getWordTop(firstVisibleWord));
                    this.bookPageScroller.scrollTop = this.getWordTop(firstVisibleWord);
                    log('Adjusted scrollTop:', this.bookPageScroller.scrollTop);
                }
            }
        }
        this.adjustTopTranslationSpans()
    }  // adjustTopWord

    public adjustTopTranslationSpans(): void {
        const translationSpans = document.querySelectorAll('.translation-span');
        let minScrollTop: number | null = null;

        const visibleTop = this.wordsContainerTopMargin;

        translationSpans.forEach((span) => {
            const spanRect = span.getBoundingClientRect();

            // Check if span is partially visible at top
            if (spanRect.bottom > visibleTop &&
                spanRect.top < visibleTop) {
                // Calculate required scroll adjustment to make this span fully visible
                const requiredScrollTop = this.bookPageScroller.scrollTop - (visibleTop - spanRect.top);

                if (minScrollTop === null || requiredScrollTop < minScrollTop) {
                    minScrollTop = requiredScrollTop;
                }
            }
        });

        // Adjust scroll position if needed
        if (minScrollTop !== null) {
            log('Adjusting scroll position for translation spans:',
                'current:', this.bookPageScroller.scrollTop,
                'new:', minScrollTop);
            this.bookPageScroller.scrollTop = minScrollTop;
        }
    }

    public async scrollUp(): Promise<void> {
        // Scroll one viewport up
        if (this.bookPageScroller.scrollTop === 0) {
            if (this.pageNumber === 1) {
                return;
            }
            await this.loadPage(this.pageNumber - 1, undefined);
            // Scroll to the bottom of the page
            this.bookPageScroller.scrollTop = this.getWordsContainerHeight() - this.bookPageScroller.clientHeight;
        } else {
            // no need to check for negative scroll top, it will be handled by the browser
            log('***** scrollTop:', this.bookPageScroller.scrollTop, 'clientHeight-lineHeight:', this.bookPageScroller.clientHeight - this.lineHeight);
            this.bookPageScroller.scrollTop -= this.bookPageScroller.clientHeight - this.lineHeight;
        }
        this.adjustTopWord();
        this.reportReadingLocation();
    }  // scrollUp

    public async scrollDown(): Promise<void> {
        // Scroll one viewport down
        const scrollerRect = this.bookPageScroller.getBoundingClientRect();
        const containerRect = this.wordsContainer.getBoundingClientRect();
        this.adjustEmptySpace();

        if (containerRect.bottom <= scrollerRect.bottom) {
            // We've reached the bottom of the current page
            await this.loadPage(this.pageNumber + 1, 0);
        } else {
            // Scroll down by viewport height minus line height
            log('FirstVisibleWord:', this.getFirstVisibleWord(), 'scrollTop:', this.bookPageScroller.scrollTop);
            this.bookPageScroller.scrollTop += this.bookPageScroller.clientHeight - this.lineHeight;
            log('FirstVisibleWord:', this.getFirstVisibleWord(), 'scrollTop:', this.bookPageScroller.scrollTop);
            log('***** scrollTop:', this.bookPageScroller.scrollTop, 'clientHeight-lineHeight:', this.bookPageScroller.clientHeight - this.lineHeight);
            this.adjustTopWord();
        }
        this.reportReadingLocation();
    }  // scrollDown

    async jump(pageNum: number, topWord: number): Promise<void> {
        const response = await fetch('/jump', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: `book-code=${this.bookCode}&book-page-number=${pageNum}&top-word=${topWord}`,
        });
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                await this.loadPage(pageNum, topWord);
                this.updateJumpButtons();
            } else {
                console.error('Jump failed:', data.error);
            }
        } else {
            console.error('Network error during jump');
        }
    }

    async jumpBack(): Promise<void> {
        const response = await fetch('/jump_back', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: `book-code=${this.bookCode}&book-page-number=${this.pageNumber}`,
        });
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                await this.loadPage(data.page_number, data.word);
                this.updateJumpButtons();
            } else {
                console.error('Jump back failed:', data.error);
            }
        } else {
            console.error('Network error during jump back');
        }
    }

    async jumpForward(): Promise<void> {
        const response = await fetch('/jump_forward', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: `book-code=${this.bookCode}&book-page-number=${this.pageNumber}`,
        });
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                await this.loadPage(data.page_number, data.word);
                this.updateJumpButtons();
            } else {
                console.error('Jump forward failed:', data.error);
            }
        } else {
            console.error('Network error during jump forward');
        }
    }

    private updateJumpButtons(): void {
        const backButton = document.getElementById('back-button') as HTMLButtonElement;
        const forwardButton = document.getElementById('forward-button') as HTMLButtonElement;

        if (backButton && forwardButton) {
            fetch(`/get_jump_status?book-code=${this.bookCode}`)
                .then(response => response.json())
                .then(data => {
                    backButton.disabled = data.is_first_jump;
                    forwardButton.disabled = data.is_last_jump;
                })
                .catch(error => console.error('Error updating jump buttons:', error));
        }
    }

    private addLinkClickListeners(): void {
        const links = this.wordsContainer.querySelectorAll('a[data-href]');
        links.forEach((link: Element) => {
            if (link instanceof HTMLElement) {
                link.addEventListener('click', (event: Event) => {
                    event.preventDefault();
                    const href = link.dataset.href;
                    if (href) {
                        this.handleLinkClick(href);
                    }
                });
            }
        });
    }

    private async handleLinkClick(href: string): Promise<void> {
        try {
            const response = await fetch('/link_click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: `book-code=${this.bookCode}&link=${encodeURIComponent(href)}`,
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            if (data.success) {
                await this.loadPage(data.page_number, data.word);
                this.updateJumpButtons();
            } else {
                console.error('Error processing link click:', data.error);
            }
        } catch (error) {
            console.error('Error handling link click:', error);
        }
    }

    private getCsrfToken(): string {
        const csrfCookie = document.cookie.split(';').find(cookie => cookie.trim().startsWith('csrftoken='));
        return csrfCookie ? csrfCookie.split('=')[1] : '';
    }

}  // Viewport

// Global instance of the Viewport class
export const viewport = new Viewport();
