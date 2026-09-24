import { TextDecoder, TextEncoder } from 'util';
import { ArticleStreamEvent, ChunkReader, escapeHtml, markdownEmphasis, readNdjson } from '../../lexiflux/viewport/articleStream';

Object.assign(global, { TextDecoder, TextEncoder });

function chunkReader(chunks: (string | Uint8Array)[]): ChunkReader {
  const encoder = new TextEncoder();
  let index = 0;
  return {
    read: () => {
      if (index >= chunks.length) {
        return Promise.resolve({ done: true });
      }
      const chunk = chunks[index++];
      return Promise.resolve({ done: false, value: typeof chunk === 'string' ? encoder.encode(chunk) : chunk });
    },
  };
}

async function collect(chunks: (string | Uint8Array)[]): Promise<ArticleStreamEvent[]> {
  const events: ArticleStreamEvent[] = [];
  await readNdjson(chunkReader(chunks), event => events.push(event));
  return events;
}

describe('readNdjson', () => {
  test('parses one event per line', async () => {
    const events = await collect(['{"event":"delta","text":"a"}\n{"event":"done"}\n']);
    expect(events).toEqual([{ event: 'delta', text: 'a' }, { event: 'done' }]);
  });

  test('joins a line split across chunks', async () => {
    const events = await collect(['{"event":"del', 'ta","text":"Hel', 'lo"}\n{"event":', '"done"}\n']);
    expect(events).toEqual([{ event: 'delta', text: 'Hello' }, { event: 'done' }]);
  });

  test('joins a multi-byte character split across chunks', async () => {
    const bytes = new TextEncoder().encode('{"event":"delta","text":"ž"}\n');
    const cut = bytes.indexOf(0xc5) + 1;
    const events = await collect([bytes.slice(0, cut), bytes.slice(cut)]);
    expect(events).toEqual([{ event: 'delta', text: 'ž' }]);
  });

  test('reads a last line without a trailing newline and skips blank lines', async () => {
    const events = await collect(['\n{"event":"delta","text":"x"}\n\n', '{"event":"done"}']);
    expect(events).toEqual([{ event: 'delta', text: 'x' }, { event: 'done' }]);
  });

  test('passes replace, error and site events through', async () => {
    const events = await collect([
      '{"event":"replace","text":"whole"}\n',
      '{"event":"error","kind":"cut_off","html":"<p>cut</p>"}\n',
      '{"event":"site","url":"https://x/y","window":false}\n',
    ]);
    expect(events.map(e => e.event)).toEqual(['replace', 'error', 'site']);
    expect(events[1].kind).toBe('cut_off');
    expect(events[2].url).toBe('https://x/y');
  });
});

describe('markdownEmphasis', () => {
  test.each([
    ['**bold** text', '<b>bold</b> text'],
    ['an *italic* word', 'an <i>italic</i> word'],
    ['*a*', '<i>a</i>'],
    ['**b** and *i*', '<b>b</b> and <i>i</i>'],
    ['<b>html</b> stays', '<b>html</b> stays'],
    ['* list item\n* another', '* list item\n* another'],
    ['2 * 3 * 4', '2 * 3 * 4'],
    ['snake*case*word', 'snake*case*word'],
    ['**unclosed bold', '**unclosed bold'],
    ['*one\nline*', '*one\nline*'],
  ])('%j -> %j', (input, expected) => {
    expect(markdownEmphasis(input)).toBe(expected);
  });
});

describe('escapeHtml', () => {
  test('escapes markup so emphasis conversion adds the only tags', () => {
    expect(markdownEmphasis(escapeHtml('<script>*x*</script> & co'))).toBe(
      '&lt;script&gt;<i>x</i>&lt;/script&gt; &amp; co',
    );
  });
});
