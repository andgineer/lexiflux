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
  <div id="words-container"></div>
`;
global.htmx = mockHtmx;

export {};
