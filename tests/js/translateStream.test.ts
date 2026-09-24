import { TextDecoder, TextEncoder } from 'util';
import fetchMock from 'jest-fetch-mock';

Object.assign(global, { TextDecoder, TextEncoder });

const mockSpanManager = {
  getExtendedWordIds: jest.fn((ids: number[]) => new Set(ids)),
  getAffectedSpans: jest.fn(() => new Set<number>()),
  addSpan: jest.fn(),
  removeSpan: jest.fn(),
};

const mockViewport = {
  bookCode: 'test-book',
  pageNumber: 5,
  adjustTopTranslationSpans: jest.fn(),
  bookPageScroller: {
    getBoundingClientRect: jest.fn().mockReturnValue({ bottom: 500 }),
    scrollTop: 0,
    offsetWidth: 800,
  },
};

class ControlledStream {
  private encoder = new TextEncoder();
  private queue: { done: boolean; value?: Uint8Array }[] = [];
  private waiting: ((result: { done: boolean; value?: Uint8Array }) => void) | null = null;
  private failWith: ((error: Error) => void) | null = null;

  reader = {
    read: (): Promise<{ done: boolean; value?: Uint8Array }> => {
      const next = this.queue.shift();
      if (next) {
        return Promise.resolve(next);
      }
      return new Promise((resolve, reject) => {
        this.waiting = resolve;
        this.failWith = reject;
      });
    },
  };

  push(text: string): void {
    this.deliver({ done: false, value: this.encoder.encode(text) });
  }

  end(): void {
    this.deliver({ done: true });
  }

  fail(error: Error): void {
    if (this.failWith) {
      const reject = this.failWith;
      this.waiting = null;
      this.failWith = null;
      reject(error);
    }
  }

  private deliver(result: { done: boolean; value?: Uint8Array }): void {
    if (this.waiting) {
      const resolve = this.waiting;
      this.waiting = null;
      this.failWith = null;
      resolve(result);
    } else {
      this.queue.push(result);
    }
  }
}

let streams: ControlledStream[] = [];
let streamSignals: AbortSignal[] = [];
let inlineArticle = 'inline';
let inlineError = false;

const flush = () => new Promise(resolve => setTimeout(resolve, 0));
const line = (event: object) => JSON.stringify(event) + '\n';
const panel = (n: number) => document.getElementById(`lexical-content-${n}`) as HTMLElement;
const streamCalls = () => fetchMock.mock.calls.filter(call => String(call[0]).startsWith('/translate/stream'));

function loadTranslate() {
  jest.resetModules();
  jest.doMock('../../lexiflux/viewport/viewport', () => ({ viewport: mockViewport }));
  jest.doMock('../../lexiflux/viewport/TranslationSpanManager', () => ({ spanManager: mockSpanManager }));
  return require('../../lexiflux/viewport/translate');
}

function selectWords(translate: any): void {
  const range = {
    startContainer: document.getElementById('word-1'),
    endContainer: document.getElementById('word-2'),
    collapsed: false,
  };
  translate.clearLexicalPanel();
  translate.sendTranslationRequest(range as any);
}

beforeEach(() => {
  streams = [];
  streamSignals = [];
  inlineArticle = 'inline';
  inlineError = false;
  jest.spyOn(console, 'log').mockImplementation();
  jest.spyOn(console, 'error').mockImplementation();

  document.body.innerHTML = `
    <div id="lexical-panel" class="show"></div>
    <div id="lexicalPanelContent">
      <div class="tab-pane active" id="lexical-article-1">
        <div id="lexical-content-1" class="lexical-content"></div>
        <iframe id="lexical-frame-1"></iframe>
      </div>
      <div class="tab-pane" id="lexical-article-2">
        <div id="lexical-content-2" class="lexical-content"></div>
        <iframe id="lexical-frame-2"></iframe>
      </div>
    </div>
    <div id="book-page-scroller">
      <div id="words-container">
        <span id="word-1" class="word">Word 1</span>
        <span id="word-2" class="word">Word 2</span>
      </div>
    </div>
  `;

  window.getSelection = jest.fn().mockReturnValue({ removeAllRanges: jest.fn(), addRange: jest.fn() });
  document.createRange = jest.fn().mockImplementation(() => ({
    setStart: jest.fn(),
    setEnd: jest.fn(),
    setStartBefore: jest.fn(),
    setEndAfter: jest.fn(),
    selectNodeContents: jest.fn(),
    cloneContents: jest.fn(() => document.createDocumentFragment()),
    deleteContents: jest.fn(),
    insertNode: jest.fn((node: Node) => document.getElementById('words-container')!.appendChild(node)),
    startContainer: document.getElementById('word-1'),
    endContainer: document.getElementById('word-2'),
  }));

  fetchMock.resetMocks();
  fetchMock.mockImplementation(((input: string, init?: RequestInit) => {
    if (String(input).startsWith('/translate/stream')) {
      const stream = new ControlledStream();
      streams.push(stream);
      streamSignals.push(init!.signal as AbortSignal);
      return Promise.resolve({ ok: true, status: 200, body: { getReader: () => stream.reader } });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ article: inlineArticle, error: inlineError }) });
  }) as any);
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('sidebar article stream', () => {
  test('requests /translate/stream with the panel number and shows a spinner until the first event', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    const calls = streamCalls();
    expect(calls).toHaveLength(1);
    expect(String(calls[0][0])).toContain('lexical-article=1');
    expect(String(calls[0][0])).toContain('word-ids=1.2');
    expect(panel(1).innerHTML).toContain('spinner-border');

    streams[0].push(line({ event: 'delta', text: 'Hel' }));
    await flush();
    expect(panel(1).innerHTML).toBe('Hel');
  });

  test('appends deltas, converts Markdown emphasis on the whole buffer, and replace resets it', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    streams[0].push(line({ event: 'delta', text: '**bo' }));
    await flush();
    expect(panel(1).innerHTML).toBe('**bo');

    streams[0].push(line({ event: 'delta', text: 'ld** and *it*' }));
    await flush();
    expect(panel(1).innerHTML).toBe('<b>bold</b> and <i>it</i>');

    streams[0].push(line({ event: 'replace', text: 'whole *answer*' }));
    await flush();
    expect(panel(1).innerHTML).toBe('whole <i>answer</i>');

    streams[0].push(line({ event: 'delta', text: '!' }));
    await flush();
    expect(panel(1).innerHTML).toBe('whole <i>answer</i>!');
  });

  test('a cut_off error is appended after the text already shown', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    streams[0].push(line({ event: 'delta', text: 'partial' }));
    streams[0].push(line({ event: 'error', kind: 'cut_off', html: '<div class="alert">cut off</div>' }));
    await flush();

    expect(panel(1).innerHTML).toBe('partial<div class="alert">cut off</div>');
  });

  test('any other error replaces the panel', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    streams[0].push(line({ event: 'delta', text: 'partial' }));
    streams[0].push(line({ event: 'error', kind: 'busy', html: '<div class="alert">busy</div>' }));
    await flush();

    expect(panel(1).innerHTML).toBe('<div class="alert">busy</div>');
  });

  test('a site event goes through the Site handling', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    streams[0].push(line({ event: 'site', url: 'https://glosbe.com/x', window: false }));
    streams[0].push(line({ event: 'done' }));
    streams[0].end();
    await flush();

    const iframe = document.getElementById('lexical-frame-1') as HTMLIFrameElement;
    expect(iframe.src).toBe('https://glosbe.com/x');
    expect(iframe.style.display).toBe('block');
    expect(panel(1).innerHTML).toBe('');
  });

  test('done marks the panel updated, so switching back to it does not request again', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    streams[0].push(line({ event: 'delta', text: 'answer' }) + line({ event: 'done' }));
    streams[0].end();
    await flush();

    translate.lexicalPanelSwitched('lexical-tab-1');
    await flush();
    expect(streamCalls()).toHaveLength(1);
    expect(panel(1).innerHTML).toBe('answer');
  });

  test('a panel still streaming is not requested again when its tab is re-shown', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    translate.lexicalPanelSwitched('lexical-tab-1');
    await flush();

    expect(streamCalls()).toHaveLength(1);
    expect(streamSignals[0].aborted).toBe(false);
  });

  test('a new selection aborts the running stream and ignores its late events', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();
    streams[0].push(line({ event: 'delta', text: 'old ' }));
    await flush();

    selectWords(translate);
    await flush();

    expect(streamSignals[0].aborted).toBe(true);
    expect(streamSignals[1].aborted).toBe(false);

    streams[0].push(line({ event: 'delta', text: 'late' }));
    streams[1].push(line({ event: 'delta', text: 'new' }));
    await flush();
    expect(panel(1).innerHTML).toBe('new');

    streams[0].fail(new DOMException('aborted', 'AbortError'));
    await flush();
    expect(panel(1).innerHTML).toBe('new');
  });

  test('a stream that ends after text without done appends the cut-off notice', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    streams[0].push(line({ event: 'delta', text: '*half* an answer' }));
    streams[0].end();
    await flush();

    expect(panel(1).innerHTML).toContain('<i>half</i> an answer');
    expect(panel(1).innerHTML).toContain('The answer was cut off');
    expect(panel(1).innerHTML).not.toContain('spinner-border');

    translate.lexicalPanelSwitched('lexical-tab-1');
    await flush();
    expect(streamCalls()).toHaveLength(2);
  });

  test('a stream that ends with nothing and no done replaces the spinner with the panel error', async () => {
    const translate = loadTranslate();
    selectWords(translate);
    await flush();
    expect(panel(1).innerHTML).toContain('spinner-border');

    streams[0].end();
    await flush();

    expect(panel(1).innerHTML).not.toContain('spinner-border');
    expect(panel(1).innerHTML).toContain('Failed to load lexical article');
  });

  test('a failed response shows the panel error', async () => {
    fetchMock.mockImplementation((() => Promise.resolve({ ok: false, status: 500 })) as any);
    const translate = loadTranslate();
    selectWords(translate);
    await flush();

    expect(panel(1).innerHTML).toContain('Failed to load lexical article');
  });
});

describe('inline popup', () => {
  test('shows Markdown emphasis and keeps other markup as text', async () => {
    inlineArticle = '**word** <x>';
    const translate = loadTranslate();
    selectWords(translate);
    await flush();
    await flush();

    const text = document.querySelector('.translation-text') as HTMLElement;
    expect(text.innerHTML).toBe('<b>word</b> &lt;x&gt;');
  });

  test('renders a server error as HTML', async () => {
    inlineArticle = '<div class="alert alert-warning"><p>No key</p></div>';
    inlineError = true;
    const translate = loadTranslate();
    selectWords(translate);
    await flush();
    await flush();

    const text = document.querySelector('.translation-text') as HTMLElement;
    expect(text.querySelector('.alert p')?.textContent).toBe('No key');
    expect(text.textContent).not.toContain('<div');
  });
});
