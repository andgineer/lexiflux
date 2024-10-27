import { showModal, closeModal } from './utils';
import { viewport } from './viewport';

export interface ReaderSettings {
    font_size: string;
    font_family: string;
}

interface FontOption {
  name: string;
  value: string;
  type: 'system' | 'google';
}

const SYSTEM_FONTS: FontOption[] = [
  { name: 'System Default', value: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif', type: 'system' },
  { name: 'Serif', value: 'serif', type: 'system' },
  { name: 'Sans-serif', value: 'sans-serif', type: 'system' },
  { name: 'Monospace', value: 'monospace', type: 'system' },
];

const GOOGLE_FONTS: FontOption[] = [
  { name: 'Roboto', value: '"Roboto", sans-serif', type: 'google' },
  { name: 'Open Sans', value: '"Open Sans", sans-serif', type: 'google' },
  { name: 'Noto Sans', value: '"Noto Sans", sans-serif', type: 'google' },
  { name: 'Lato', value: '"Lato", sans-serif', type: 'google' },
];

const ALL_FONTS = [...SYSTEM_FONTS, ...GOOGLE_FONTS];

const DEFAULT_FONT_SIZE = '16px';
const DEFAULT_FONT_FAMILY = SYSTEM_FONTS[0].value;

// Functions
function loadGoogleFonts(): void {
  // Check if Google Fonts are already loaded
  const existingLink = document.querySelector('link[href*="fonts.googleapis.com"]');
  if (existingLink) {
    return;
  }

  const link = document.createElement('link');
  link.rel = 'stylesheet';

  // Add weights and styles for better font rendering
  const fontsWithWeights = GOOGLE_FONTS.map(font => {
    const fontName = font.name.replace(' ', '+');
    return `family=${fontName}:wght@400;500;700&display=swap`;
  }).join('&');

  link.href = `https://fonts.googleapis.com/css2?${fontsWithWeights}`;

  // Add onload handler to ensure fonts are loaded
  link.onload = () => {
    console.log('Google Fonts loaded successfully');
    // Force a redraw of the preview text
    const previewText = document.getElementById('fontPreviewText');
    if (previewText) {
      const currentFont = (document.getElementById('fontFamilySelect') as HTMLSelectElement)?.value;
      if (currentFont) {
        previewText.style.fontFamily = currentFont;
      }
    }
  };

  link.onerror = (err) => {
    console.error('Failed to load Google Fonts:', err);
  };

  document.head.appendChild(link);
}

function getInitialSettings(): ReaderSettings {
  const settingsData = document.getElementById('reader-settings-data');

  const settings: ReaderSettings = {
    font_size: DEFAULT_FONT_SIZE,
    font_family: DEFAULT_FONT_FAMILY
  };

  if (settingsData) {
    const fontFamily = settingsData.dataset.fontFamily;
    const fontSize = settingsData.dataset.fontSize;

    if (fontFamily) {
      settings.font_family = fontFamily;
    }

    if (fontSize) {
      settings.font_size = fontSize;
    }
  }

  return settings;
}

function applyReaderSettings(settings: ReaderSettings): void {
  const wordsContainer = viewport.getWordsContainer();
  if (wordsContainer) {
    wordsContainer.style.fontSize = settings.font_size;
    wordsContainer.style.fontFamily = settings.font_family;
  }
}

async function saveReaderSettings(settings: ReaderSettings): Promise<void> {
    try {
        const formData = new FormData();
        formData.append('book_code', viewport.bookCode);
        formData.append('font_family', settings.font_family);
        formData.append('font_size', settings.font_size);

        const response = await fetch('/api/reader-settings/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Failed to save reader settings:', errorText);
            throw new Error(errorText);
        }
    } catch (error) {
        console.error('Error saving reader settings:', error);
        throw error;
    }
}

function getCsrfToken(): string {
  const csrfCookie = document.cookie
    .split(';')
    .find(cookie => cookie.trim().startsWith('csrftoken='));
  return csrfCookie ? csrfCookie.split('=')[1] : '';
}

function handleReaderSettingsSubmit(): void {
  const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;
  const familySelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;

  if (sizeSelect && familySelect) {
    const newSettings: ReaderSettings = {
      font_size: sizeSelect.value,
      font_family: familySelect.value
    };

    applyReaderSettings(newSettings);
    saveReaderSettings(newSettings)
      .then(() => {
        console.log('Reader settings saved successfully');
        closeModal('fontSettingsModal');
      })
      .catch(error => {
        console.error('Failed to save reader settings:', error);
        // Optionally show an error message to the user
      });
  }
}

function handleReaderSettingsButtonClick(event: Event): void {
  event.preventDefault();
  showModal('fontSettingsModal');
}

function handleFontSelectChange(event: Event): void {
  const select = event.target as HTMLSelectElement;
  const previewText = document.getElementById('fontPreviewText');

  if (previewText) {
    previewText.style.fontFamily = select.value;
  }
}

export function initializeReaderSettings(): void {
  // Load Google Fonts first
  loadGoogleFonts();

  const initialSettings = getInitialSettings();

  const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;
  const familySelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;

  if (familySelect) {
    // Clear existing options
    familySelect.innerHTML = '';

    // Populate font select with all available options
    ALL_FONTS.forEach(font => {
      const option = document.createElement('option');
      option.value = font.value;
      option.textContent = font.name;
      option.setAttribute('data-font-type', font.type);
      familySelect.appendChild(option);
    });

    // Set the initial font family
    familySelect.value = initialSettings.font_family;
  }

  if (sizeSelect) {
    sizeSelect.value = initialSettings.font_size;
  }

  // Update preview text with initial font
  const previewText = document.getElementById('fontPreviewText');
  if (previewText) {
    previewText.style.fontFamily = initialSettings.font_family;
  }
}
export function initializeReaderEventListeners(): void {
  let fontSettingsButton = document.getElementById('font-settings-button');
  if (fontSettingsButton) {
    fontSettingsButton.removeEventListener('click', handleReaderSettingsButtonClick);
    fontSettingsButton.addEventListener('click', handleReaderSettingsButtonClick);
  }

  const fontSettingsSubmit = document.getElementById('fontSettingsSubmit');
  if (fontSettingsSubmit) {
    fontSettingsSubmit.removeEventListener('click', handleReaderSettingsSubmit);
    fontSettingsSubmit.addEventListener('click', handleReaderSettingsSubmit);
  }

  const fontFamilySelect = document.getElementById('fontFamilySelect');
  if (fontFamilySelect) {
    fontFamilySelect.removeEventListener('change', handleFontSelectChange);
    fontFamilySelect.addEventListener('change', handleFontSelectChange);
  }
}
