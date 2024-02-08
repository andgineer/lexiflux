import fetchMock from 'jest-fetch-mock';

fetchMock.enableMocks();

const mockHtmx = { process: jest.fn() };

declare global {
  var htmx: typeof mockHtmx;
  var numberOfWords: number;
}
global.htmx = mockHtmx;
global.numberOfWords = 5;

let wordSpans = "";
for (let i = 0; i < global.numberOfWords; i++) {
    wordSpans += `<span id='word-${i}' class='word'>word${i}</span>`;
}

global.document.body.innerHTML = `
<div id="top-navbar"></div>
<div id="book-page-scroller" style="height: 500px;">  
  <div id="words-container">
  ${wordSpans}
  </div>
</div>
<div id="book" data-book-id="123" data-book-page-number="1" data-click-word-url="/click-word"></div>
`;

import {viewport} from "../../lexiflux/viewport/viewport";  // load the module only after the DOM is set up

const containerHeight = 60;
const containerRect: DOMRect = {
  top: 0,
  bottom: containerHeight,
  left: 0,
  right: 100,
  width: 100,
  height: containerHeight,
  x: 0,
  y: 0,
  toJSON: () => {
  }, // Adding the toJSON method to satisfy TypeScript
};
const mockContainerRectFunc = (): DOMRect => containerRect;

Object.defineProperty(viewport.wordsContainer, 'getBoundingClientRect', {
  value: () => mockContainerRectFunc
});

beforeEach(() => {
  // Clear all mocks before each test
  fetchMock.resetMocks();

  // Define a base URL for the purpose of testing
  const baseURL = 'http://localhost';

  // Mock fetch calls to handle relative URLs by prepending the base URL
  fetchMock.mockIf((req) => {
    const requestUrl = typeof req === 'string' ? req : req.url;
    // Check if the URL is already absolute; if not, consider it a relative URL
    return !requestUrl.startsWith('http');
  }, async (req) => {
    const requestUrl = typeof req === 'string' ? req : req.url;
    const absoluteUrl = `${baseURL}${requestUrl}`;

    // Now, check the absolute URL to determine how to mock responses
    if (absoluteUrl.includes('/page')) {
      return {
        status: 200,
        body: JSON.stringify({
          html: global.document.body.innerHTML,
          data: {
            bookId: '123',
            pageNum: '1',
            pageHtml: wordSpans,
          },
        }),
      };
    } else if (absoluteUrl.includes('/position')) {
      return {
        status: 200,
        body: JSON.stringify('Position updated successfully'),
      };
    } else if (absoluteUrl.includes('/translate')) {
      return {
        status: 200,
        body: JSON.stringify({
          translatedText: 'translated text',
          article: 'translated article',
        }),
      };
    };
    // Fallback for unmocked endpoints
    console.log('Unknown endpoint:', absoluteUrl);
    return {
        status: 500,
        body: JSON.stringify('Unknown endpoint'),
      };
  });
});



