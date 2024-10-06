new Vue({
    el: '#app',
    delimiters: ['${', '}'],
    data: {
        availableLanguages: JSON.parse('{{ languages|escapejs }}'),
        availableLanguageGroups: JSON.parse('{{ language_groups|escapejs }}'),
        selectedLanguage: null,
        minDateTime: '',
        successMessage: '',
        errorMessage: '',
        exportMethod: '{{ last_export_format|escapejs }}',
        isExporting: false,
        wordCount: {{ initial_word_count }},
        deckName: '{{ default_deck_name|escapejs }}',
        previousDeckNames: JSON.parse('{{ previous_deck_names|escapejs }}'),
        showDeckNameDropdown: false,
    },
    computed: {
        selectedLanguageId() {
            if (!this.selectedLanguage) return null;
            return this.selectedLanguage.id || this.selectedLanguage.google_code;
        },
        hasTranslations() {
            return this.availableLanguages.length > 0 || this.availableLanguageGroups.length > 0;
        },
        canExport() {
            return this.wordCount > 0;
        },
        buttonText() {
            if (this.isExporting) {
                return 'Exporting...';
            }
            if (this.wordCount === 0) {
                return 'No words to export';
            }
            return `Export ${this.wordCount} word${this.wordCount !== 1 ? 's' : ''}`;
        }
    },
    methods: {
        setDefaultSelection() {
            const defaultSelection = '{{ default_selection|escapejs }}';
            if (defaultSelection) {
                if (isNaN(defaultSelection)) {
                    // It's a language
                    this.selectedLanguage = this.availableLanguages.find(lang => lang.google_code === defaultSelection);
                } else {
                    // It's a language group
                    this.selectedLanguage = this.availableLanguageGroups.find(group => group.id === parseInt(defaultSelection));
                }
            }
        },
        updateMinDateTime() {
            if (!this.selectedLanguageId) {
                this.minDateTime = '';
                this.wordCount = 0;
                return;
            }

            if (this.hasTranslations) {
                this.errorMessage = '';
            }

            fetch(`{% url "last_export_datetime" %}?language=${this.selectedLanguageId}`)
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.error || 'An error occurred');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    // Convert the ISO string to the format expected by the datetime-local input
                    const date = new Date(data.last_export_datetime);
                    this.minDateTime = date.toISOString().slice(0, 16);
                    this.updateWordCount();
                })
                .catch(error => {
                    this.errorMessage = 'Error fetching last export date: ' + error.message;
                    this.minDateTime = '';
                    this.wordCount = 0;
                });
        },
        updateWordCount() {
            if (!this.selectedLanguageId || !this.minDateTime) {
                this.wordCount = 0;
                return;
            }

            fetch(`{% url "word_count" %}?language=${this.selectedLanguageId}&min_datetime=${this.minDateTime}`)
                .then(response => response.json())
                .then(data => {
                    this.wordCount = data.word_count;
                })
                .catch(error => {
                    console.error('Error fetching word count:', error);
                    this.wordCount = 0;
                });
        },
        exportWords() {
            if (!this.canExport || this.isExporting) {
                return;
            }

            this.successMessage = '';
            if (this.hasTranslations) {
                this.errorMessage = '';
            }
            this.isExporting = true;

            // Convert the minDateTime back to ISO format for sending to the server
            const minDateTimeISO = new Date(this.minDateTime).toISOString();

            fetch('{% url "export_words" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({
                    language: this.selectedLanguageId.toString(),
                    min_datetime: minDateTimeISO,
                    export_method: this.exportMethod,
                    deck_name: this.deckName,
                })
            })
            .then(response => {
                this.isExporting = false;
                const contentType = response.headers.get('Content-Type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json().then(data => {
                        if (data.status === 'success') {
                            this.successMessage = `Successfully exported words to Anki.`;
                            if (data.exported_words !== this.wordCount) {
                                const skippedCount = this.wordCount - data.exported_words;
                                const wordForm = skippedCount === 1 ? 'word' : 'words';
                                this.successMessage += ` ${skippedCount} ${wordForm} ${skippedCount === 1 ? 'was' : 'were'} skipped due to duplication.`;
                            }
                            this.refreshExportData();
                        } else {
                            throw new Error(data.error || 'An error occurred during export.');
                        }
                    });
                } else if (contentType && (contentType.includes('application/octet-stream') || contentType.includes('text/csv'))) {
                    return response.blob().then(blob => {
                        const filename = response.headers.get('Content-Disposition').split('filename=')[1].replace(/"/g, '');
                        this.saveFile(blob, filename);
                        this.refreshExportData();
                    });
                } else {
                    throw new Error('Unexpected response from server');
                }
            })
            .catch(error => {
                this.isExporting = false;
                this.errorMessage = 'Error exporting words: ' + error.message;
            });
        },
        refreshExportData() {
            // Add a small delay to ensure server-side processes have completed
            setTimeout(() => {
                this.updateMinDateTime();
            }, 100);
        },
        saveFile(blob, suggestedName) {
            if ('showSaveFilePicker' in window) {
                window.showSaveFilePicker({
                    suggestedName: suggestedName,
                    types: [{
                        description: 'Export File',
                        accept: {'application/octet-stream': ['.apkg'], 'text/csv': ['.csv']}
                    }],
                })
                .then(handle => handle.createWritable())
                .then(writable => {
                    writable.write(blob);
                    return writable.close();
                })
                .catch(err => {
                    if (err.name !== 'AbortError') {
                        console.error('Failed to save the file:', err);
                        this.errorMessage = 'Failed to save the file. ' + err.message;
                    }
                });
            } else {
                // Fallback for browsers that don't support the File System Access API
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = suggestedName;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            }
        },
        selectDeckName(name) {
            this.deckName = name;
            this.showDeckNameDropdown = false;
        },
        onDeckNameBlur() {
            // Delay hiding the dropdown to allow for item selection
            setTimeout(() => {
                this.showDeckNameDropdown = false;
            }, 200);
        },
    },
    watch: {
        selectedLanguage: {
            handler(newVal) {
                if (newVal) {
                    this.updateMinDateTime();
                } else {
                    this.minDateTime = '';
                    this.wordCount = 0;
                    if (this.hasTranslations) {
                        this.errorMessage = '';
                    }
                }
            },
            immediate: true
        },
        minDateTime() {
            this.updateWordCount();
        },
    },
    created() {
        if (!this.hasTranslations) {
            this.errorMessage = 'Your translation history is empty. Please translate some words before exporting.';
        }
    },
    mounted() {
        this.setDefaultSelection();
        var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
        var dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
            return new bootstrap.Dropdown(dropdownToggleEl)
        });
    }
});