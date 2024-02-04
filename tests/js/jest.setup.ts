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
<div id="book-page-scroller">  
  <div id="words-container">
  ${wordSpans}
  </div>
</div>
<div id="book" data-book-id="123" data-book-page-number="1" data-click-word-url="/click-word"></div>
`;

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
    }
    // Fallback for unmocked endpoints
    return Promise.reject(new Error(`Unmocked request: ${absoluteUrl}`));
  });
});



