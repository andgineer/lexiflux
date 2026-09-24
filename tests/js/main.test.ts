jest.mock('../../lexiflux/viewport/viewport', () => ({ viewport: {} }));
jest.mock('../../lexiflux/viewport/readerSettings', () => ({
  initializeReaderSettings: jest.fn(),
  initializeReaderEventListeners: jest.fn(),
}));
jest.mock('../../lexiflux/viewport/translate', () => ({
  sendTranslationRequest: jest.fn(),
  lexicalPanelSwitched: jest.fn(),
  clearLexicalPanel: jest.fn(),
  hideTranslation: jest.fn((span: HTMLElement) => span.remove()),
}));

import { handleMouseUpEvent } from '../../lexiflux/viewport/main';
import { hideTranslation } from '../../lexiflux/viewport/translate';

describe('handleMouseUpEvent on a translation span', () => {
  beforeEach(() => {
    (hideTranslation as jest.Mock).mockClear();
    document.body.innerHTML = `
      <div id="book-page-scroller">
        <span class="translation-span" id="translation-word-1">
          <div class="translation-text">
            <div class="alert"><p>Pick another translator in
              <a href="/language-preferences/" class="alert-link">Language Preferences</a>.</p></div>
          </div>
        </span>
      </div>`;
  });

  function mouseUpOn(target: Element): void {
    const event = new MouseEvent('mouseup', { bubbles: true });
    Object.defineProperty(event, 'target', { value: target });
    handleMouseUpEvent(event);
  }

  it('keeps the span when the mouseup is on a link inside it', () => {
    mouseUpOn(document.querySelector('.alert-link')!);

    expect(hideTranslation).not.toHaveBeenCalled();
    expect(document.querySelector('.translation-span')).not.toBeNull();
  });

  it('hides the span when the mouseup is on its text', () => {
    mouseUpOn(document.querySelector('.alert p')!);

    expect(hideTranslation).toHaveBeenCalledTimes(1);
    expect(document.querySelector('.translation-span')).toBeNull();
  });
});

describe('handleMouseUpEvent on a translation span inside a book link', () => {
  beforeEach(() => {
    (hideTranslation as jest.Mock).mockClear();
    document.body.innerHTML = `
      <div id="book-page-scroller">
        <a href="#footnote-1" class="book-link"></a>
      </div>`;
    // The HTML parser would split nested <a> tags, so the popup is attached via DOM as translate.ts does.
    const span = document.createElement('span');
    span.className = 'translation-span';
    span.innerHTML = `
      <div class="translation-text">
        <p>Pick another translator in
          <a href="/language-preferences/" class="alert-link">Language Preferences</a>.</p>
      </div>
      <div class="original-text"><span class="word">note</span></div>`;
    document.querySelector('.book-link')!.appendChild(span);
  });

  function mouseUpOn(target: Element): void {
    const event = new MouseEvent('mouseup', { bubbles: true });
    Object.defineProperty(event, 'target', { value: target });
    handleMouseUpEvent(event);
  }

  it('hides the span when the mouseup is on its plain text', () => {
    mouseUpOn(document.querySelector('.translation-text p')!);

    expect(hideTranslation).toHaveBeenCalledTimes(1);
    expect(document.querySelector('.translation-span')).toBeNull();
  });

  it('keeps the span when the mouseup is on its own link', () => {
    mouseUpOn(document.querySelector('.alert-link')!);

    expect(hideTranslation).not.toHaveBeenCalled();
    expect(document.querySelector('.translation-span')).not.toBeNull();
  });
});
