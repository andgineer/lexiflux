const languageFlags = {
    'af': '🇿🇦', 'sq': '🇦🇱', 'am': '🇪🇹', 'ar': '🇸🇦', 'hy': '🇦🇲', 'az': '🇦🇿',
    'eu': '🇪🇸', 'be': '🇧🇾', 'bn': '🇧🇩', 'bs': '🇧🇦', 'bg': '🇧🇬', 'ca': '🇪🇸',
    'zh-CN': '🇨🇳', 'zh-TW': '🇹🇼', 'hr': '🇭🇷', 'cs': '🇨🇿', 'da': '🇩🇰', 'nl': '🇳🇱',
    'en': '🇬🇧', 'et': '🇪🇪', 'fil': '🇵🇭', 'fi': '🇫🇮', 'fr': '🇫🇷', 'gl': '🇪🇸',
    'ka': '🇬🇪', 'de': '🇩🇪', 'el': '🇬🇷', 'gu': '🇮🇳', 'ht': '🇭🇹', 'he': '🇮🇱',
    'hi': '🇮🇳', 'hu': '🇭🇺', 'is': '🇮🇸', 'id': '🇮🇩', 'ga': '🇮🇪', 'it': '🇮🇹',
    'ja': '🇯🇵', 'kn': '🇮🇳', 'kk': '🇰🇿', 'km': '🇰🇭', 'ko': '🇰🇷', 'ky': '🇰🇬',
    'lo': '🇱🇦', 'lv': '🇱🇻', 'lt': '🇱🇹', 'mk': '🇲🇰', 'ms': '🇲🇾', 'ml': '🇮🇳',
    'mt': '🇲🇹', 'mr': '🇮🇳', 'mn': '🇲🇳', 'my': '🇲🇲', 'ne': '🇳🇵', 'no': '🇳🇴',
    'fa': '🇮🇷', 'pl': '🇵🇱', 'pt': '🇵🇹', 'pa': '🇮🇳', 'ro': '🇷🇴', 'ru': '🇷🇺',
    'sr': '🇷🇸', 'si': '🇱🇰', 'sk': '🇸🇰', 'sl': '🇸🇮', 'es': '🇪🇸', 'sw': '🇰🇪',
    'sv': '🇸🇪', 'ta': '🇮🇳', 'te': '🇮🇳', 'th': '🇹🇭', 'tr': '🇹🇷', 'uk': '🇺🇦',
    'ur': '🇵🇰', 'uz': '🇺🇿', 'vi': '🇻🇳', 'cy': '🇬🇧', 'yi': '🇮🇱'
};
new Vue({
    el: '#language-preferences-editor',
    delimiters: ['[[', ']]'],
    components: {
        'draggable': vuedraggable,
    },
    data: function() {
        let data = {
            articles: [],
            aiModels: JSON.parse('{{ ai_models|escapejs }}'),
            availableDictionaries: JSON.parse('{{ translators|escapejs }}'),
            predefinedUrls: [
                'https://glosbe.com/{langCode}/{toLangCode}/{term}',
                'https://www.wordreference.com/{langCode}{toLangCode}/{term}',
                'https://translate.google.com/?sl={langCode}&tl={toLangCode}&text={term}&op=translate',
                'https://www.linguee.com/{lang}-{toLang}/search?source=auto&query={term}',
                'https://en.bab.la/dictionary/{lang}-{toLang}/{term}',
                'https://dictionary.reverso.net/{lang}-{toLang}/{word}',
                'https://en.pons.com/translate?q={term}&l={langCode}{toLangCode}&in=&lf=en&qnac=',
                'https://www.multitran.com/m.exe?ll1=114&ll2=2&s={term}',
            ],
            form: {
                id: null,
                title: '',
                type: '',
                parameters: {}
            },
            showTitleField: true,
            modalTitle: '',
            titleManuallyEdited: false,
            allLanguages: {
                withPreferences: [],
                withoutPreferences: []
            },
            allLanguagesFlat: [],
            languageFlags: languageFlags,
            currentLanguageId: null,
            userLanguageId: null,
            inlineTranslation: {},
            errorMessage: '',
            deleteArticleId: null,
            deleteArticleTitle: '',
            deleteErrorMessage: '',
            titlePlaceholder: "Leave empty to autofill",
            aiPromptPlaceholder: `Enter AI chat prompt here. For example:

You will be given a text in {text_language} language.
ONE word or phrase is marked with [WORD_START][WORD_END]
Give me synonyms and antonyms of the marked word.
Add to each translation to {user_language} language.
`
        };

        try {
            data.articles = JSON.parse('{{ articles|escapejs }}' || '[]');
        } catch (e) {
            console.error('Error parsing articles:', e);
        }

        try {
            data.inlineTranslation = JSON.parse('{{ inline_translation|escapejs }}' || '{}');
        } catch (e) {
            console.error('Error parsing inline translation:', e);
        }

        data.currentLanguageId = '{{ default_language_preferences.language.google_code }}' || null;
        data.userLanguageId = '{{ default_language_preferences.user_language.google_code }}' || null;

        return data;
    },
    mounted: function() {
        this.updateLanguagePreferences();
    },
    computed: {
        groupedLanguages() {
            return [
                { label: 'Languages with Preferences', options: this.allLanguages.withPreferences },
                { label: 'Other Languages', options: this.allLanguages.withoutPreferences }
            ];
        }
    },
    watch: {
        'form.parameters.url': function() {
            if (this.form.type === 'Site') {
                this.updateTitle();
            }
        },
        'form.parameters.dictionary': function() {
            if (this.form.type === 'Dictionary') {
                this.updateTitle();
            }
        }
    },
    methods: {
        updateLanguagePreferences() {
            fetch('{% url "get_language_preferences" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({ language_id: this.currentLanguageId }),
                credentials: 'include'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    this.articles = data.articles;
                    this.inlineTranslation = data.inline_translation;
                    this.userLanguageId = data.user_language_id;
                    this.loadLanguages(JSON.stringify(data.all_languages), JSON.stringify(data.all_languages_flat));
                } else {
                    throw new Error(data.message || 'Failed to update language preferences');
                }
            })
            .catch(error => {
                console.error('Error updating language preferences:', error);
                this.errorMessage = 'Failed to update language preferences. Please try again.';
            });
        },
        changeLanguage() {
            this.updateLanguagePreferences();
        },
        getSelectedLanguageFlag() {
            const selectedLanguage = this.allLanguagesFlat.find(lang => lang.google_code === this.currentLanguageId);
            return selectedLanguage ? languageFlags[selectedLanguage.google_code] : '🏳️';
        },
        loadLanguages(groupedLanguagesJson, flatLanguagesJson) {
            try {
                let parsedLanguages = JSON.parse(groupedLanguagesJson || '{}');
                this.allLanguages.withPreferences = parsedLanguages.with_preferences || [];
                this.allLanguages.withoutPreferences = parsedLanguages.without_preferences || [];
            } catch (e) {
                console.error('Error parsing grouped languages:', e);
            }

            try {
                this.allLanguagesFlat = JSON.parse(flatLanguagesJson || '[]');
            } catch (e) {
                console.error('Error parsing flat languages:', e);
            }
        },
        changeUserLanguage() {
            fetch('{% url "api_update_user_language" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({
                    language_id: this.userLanguageId,
                    language_preferences_language_id: this.currentLanguageId
                }),
                credentials: 'include'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    alert('Failed to update user language: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating user language');
            });
        },
        openModal(action, article = null) {
            this.resetForm();
            this.errorMessage = '';
            this.titleManuallyEdited = false;
            this.modalTitle = action === 'add' ? 'Add New Article' : 'Edit Article';
            if (article) {
                this.form = JSON.parse(JSON.stringify(article));
                this.form.id = article.id;
                // Ensure correct parameters structure
                if (this.form.type === 'Site') {
                    this.form.parameters = {
                        url: this.form.parameters.url || '',
                        window: this.form.parameters.window || false
                    };
                } else if (this.form.type === 'Dictionary') {
                    this.form.parameters = {
                        dictionary: this.form.parameters.dictionary || ''
                    };
                }
                this.showTitleField = true;
                this.titleManuallyEdited = true;
            } else {
                this.showTitleField = true;
                // Set a default type and generate a title
                this.form.type = 'Translate';
                this.updateParameters();
            }
            new bootstrap.Modal(this.$refs.articleModal).show();
        },
        resetForm() {
            this.form = {
                id: null,
                title: '',
                type: '',
                parameters: {}
            };
            this.titleManuallyEdited = false;
        },
        formatUrl(url) {
            try {
                let domain = new URL(url).hostname;
                domain = domain.replace(/^www\./, '');
                domain = domain.replace(/\.com$/, '');
                return domain;
            } catch (e) {
                return url;  // Return the original string if it's not a valid URL
            }
        },
        getModelTitle(modelKey) {
            const model = this.aiModels.find(m => m.key === modelKey);
            return model ? model.title : modelKey;
        },
        updateParameters() {
            const oldType = this.form.type;
            const oldModel = this.form.parameters ? this.form.parameters.model : null;

            if (this.form.type === 'Site') {
                this.form.parameters = this.form.parameters || {};
                if (!('url' in this.form.parameters)) {
                    this.form.parameters.url = '';
                }
                // Set window to true if it's not already defined
                if (!('window' in this.form.parameters)) {
                    this.form.parameters.window = true;
                }
            } else if (['Translate', 'Sentence', 'Explain', 'Examples', 'Lexical'].includes(this.form.type)) {
                if (!this.form.parameters || !this.form.parameters.model) {
                    this.form.parameters = this.form.parameters || {};
                    this.form.parameters.model = this.aiModels.length > 0 ? this.aiModels[0].key : '';
                }
            } else if (this.form.type === 'Dictionary') {
                this.form.parameters = this.form.parameters || {};
                if (!this.form.parameters.dictionary && this.availableDictionaries.length > 0) {
                    this.form.parameters.dictionary = this.availableDictionaries[0].value;
                }
            }

            if (oldType !== this.form.type || oldModel !== this.form.parameters.model || !this.form.title || !this.titleManuallyEdited) {
                const newTitle = this.generateTitle(this.form.type);
                if (!this.form.title || !this.titleManuallyEdited) {
                    this.form.title = newTitle;
                    this.titleManuallyEdited = false;
                }
            }
        },
        handleTitleChange() {
            this.titleManuallyEdited = this.form.title.trim() !== '';
        },
        updateTitle() {
            if (!this.titleManuallyEdited) {
                const newTitle = this.generateTitle(this.form.type);
                this.form.title = newTitle;
            }
        },
        generateTitle(type) {
            let title = type;

            if (type === 'Site') {
                const url = this.form.parameters.url;
                if (url) {
                    title = this.formatUrl(url);
                }
            } else if (type === 'Dictionary') {
                title = this.form.parameters.dictionary || title;
            } else if (this.form.parameters && this.form.parameters.model) {
                const model = this.aiModels.find(m => m.key === this.form.parameters.model);
                if (model && model.suffix) {
                    title = `${type} ${model.suffix}`;
                }
            }

            let uniqueTitle = title;
            let counter = 1;
            while (this.articles.some(a => a.title === uniqueTitle)) {
                uniqueTitle = `${title} ${counter}`;
                counter++;
            }
            return uniqueTitle;
        },
        validateForm() {
            if (this.form.type === 'Site' && !this.form.parameters.url) {
                this.errorMessage = 'Please enter a URL for the Site type article.';
                return false;
            }
            if (this.form.type === 'Dictionary' && !this.form.parameters.dictionary) {
                this.errorMessage = 'Please select a dictionary for the Dictionary type article.';
                return false;
            }
            // Add more validations as needed
            return true;
        },
        saveArticle() {
            if (!this.validateForm()) {
                return;
            }
            const action = this.form.id ? 'edit' : 'add';
            const isInlineTranslation = !this.showTitleField;

            let url = isInlineTranslation ? '{% url "save_inline_translation" %}' : '{% url "manage_lexical_article" %}';
            let data;

            if (isInlineTranslation) {
                data = { type: this.form.type, parameters: this.form.parameters, language_id: this.currentLanguageId };
            } else {
                // Ensure correct parameters for each type
                if (this.form.type === 'Site') {
                    this.form.parameters = {
                        url: this.form.parameters.url || '',
                        window: this.form.parameters.window || false
                    };
                } else if (this.form.type === 'Dictionary') {
                    this.form.parameters = {
                        dictionary: this.form.parameters.dictionary || ''
                    };
                }
                data = { action, ...this.form, language_id: this.currentLanguageId };
            }

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify(data),
                credentials: 'include'
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    if (isInlineTranslation) {
                        this.inlineTranslation = data.inline_translation;
                    } else {
                        this.updateLanguagePreferences();
                    }
                    const modal = bootstrap.Modal.getInstance(this.$refs.articleModal);
                    modal.hide();
                } else {
                    this.errorMessage = `An error occurred while saving the article: ${data.message || 'An error occurred'}`;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (this.form.type === 'Site' && !this.form.parameters.url) {
                    this.errorMessage = 'Please enter a URL for the Site type article.';
                } else {
                    this.errorMessage = error.message || 'An error occurred while saving the article. Please check your inputs and try again.';
                }
            });
        },
        deleteArticle(id) {
            const article = this.articles.find(a => a.id === id);
            if (article) {
                this.deleteArticleId = id;
                this.deleteArticleTitle = article.title;
                this.deleteErrorMessage = '';
                new bootstrap.Modal(this.$refs.deleteConfirmModal).show();
            } else {
                console.error('Article not found');
                // Optionally, show an error message to the user
            }
        },
        confirmDelete() {
            fetch('{% url "manage_lexical_article" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({
                    action: 'delete',
                    id: this.deleteArticleId,
                    language_id: this.currentLanguageId
                }),
                credentials: 'include'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.updateLanguagePreferences();
                    bootstrap.Modal.getInstance(this.$refs.deleteConfirmModal).hide();
                } else {
                    this.deleteErrorMessage = data.message || 'An error occurred while deleting the article';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.deleteErrorMessage = 'An error occurred while deleting the article';
            });
        },
        editInlineTranslation() {
            this.resetForm();
            this.errorMessage = '';
            this.showTitleField = false;
            this.modalTitle = 'Edit In-line Translation';
            this.form.type = this.inlineTranslation.type;

            // Set up parameters based on the type
            if (this.form.type === 'Site') {
                this.form.parameters = {
                    url: this.inlineTranslation.parameters.url || '',
                    window: this.inlineTranslation.parameters.window || false
                };
            } else if (this.form.type === 'Dictionary') {
                this.form.parameters = {
                    dictionary: this.inlineTranslation.parameters.dictionary || ''
                };
            } else {
                this.form.parameters = JSON.parse(JSON.stringify(this.inlineTranslation.parameters));
            }

            new bootstrap.Modal(this.$refs.articleModal).show();
        },
        truncateText(text, maxLength) {
          if (text.length <= maxLength) {
            return text;
          }
          return text.slice(0, 15) + "...";
        },
        onDragEnd(event) {
          const { newIndex, oldIndex } = event;
          const movedArticle = this.articles[newIndex];

          // Send the new order to the server
          fetch('{% url "update_article_order" %}', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': '{{ csrf_token }}'
            },
            body: JSON.stringify({
              article_id: movedArticle.id,
              new_index: newIndex,
              language_id: this.currentLanguageId
            })
          })
          .then(response => response.json())
          .then(data => {
            if (data.status === 'success') {
              console.log('Article order updated successfully');
            } else {
              console.error('Failed to update article order:', data.message);
              // Revert the change if the server update failed
              const articlesCopy = [...this.articles];
              const [removed] = articlesCopy.splice(newIndex, 1);
              articlesCopy.splice(oldIndex, 0, removed);
              this.articles = articlesCopy;
            }
          });
        },
    }
});