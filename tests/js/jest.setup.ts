/**
 * @jest-environment jsdom
 */

const mockHtmx = {
  process: jest.fn(),
};

declare global {
  var htmx: typeof mockHtmx;
}

global.document.body.innerHTML = `
<div id="top-navbar"></div>
<div id="book-page-scroller">  
  <div id="words-container"></div>
</div>
<div id="book" data-book-id="123" data-page-number="1" data-click-word-url="/click-word"></div>
`;

global.htmx = mockHtmx;

export {};
