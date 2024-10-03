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
        exportMethod: 'ankiConnect',
        isExporting: false,
        noTranslations: JSON.parse('{{ no_translations|escapejs }}')
    },
    computed: {
        selectedLanguageId() {
            if (!this.selectedLanguage) return null;
            return this.selectedLanguage.id || this.selectedLanguage.google_code;
        },
        hasAvailableLanguages() {
            return this.availableLanguages.length > 0 || this.availableLanguageGroups.length > 0;
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
                return;
            }

            if (!this.noTranslations) {
                this.errorMessage = '';
            }
            this.successMessage = ''; // Clear any previous success message

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
                })
                .catch(error => {
                    this.errorMessage = 'Error fetching last export date: ' + error.message;
                    this.minDateTime = '';
                });
        },
        exportWords() {
            if (!this.selectedLanguageId) {
                this.errorMessage = 'Please select a language or language group.';
                return;
            }

            if (!this.noTranslations) {
                this.errorMessage = '';
            }
            this.successMessage = '';
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
                    export_method: this.exportMethod
                })
            })
            .then(response => {
                this.isExporting = false;
                const contentType = response.headers.get('Content-Type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json().then(data => {
                        if (data.status === 'success') {
                            this.successMessage = `Words exported successfully! ${data.exported_words} words exported.`;
                        } else {
                            throw new Error(data.error || 'An error occurred during export.');
                        }
                    });
                } else if (contentType && (contentType.includes('application/octet-stream') || contentType.includes('text/csv'))) {
                    return response.blob().then(blob => {
                        const filename = response.headers.get('Content-Disposition').split('filename=')[1].replace(/"/g, '');
                        this.saveFile(blob, filename);
                        // Extract the word count from the filename (assuming it's included)
                        const wordCount = filename.match(/(\d+)_words/);
                        if (wordCount) {
                            this.successMessage = `File "${filename}" has been saved successfully. ${wordCount[1]} words exported.`;
                        } else {
                            this.successMessage = `File "${filename}" has been saved successfully.`;
                        }
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
        checkTranslationHistory() {
            if (this.noTranslations) {
                this.errorMessage = 'Your translation history is empty. Please translate some words before exporting.';
            }
        }
    },
    watch: {
        selectedLanguage: {
            handler(newVal) {
                if (newVal) {
                    this.updateMinDateTime();
                } else {
                    this.minDateTime = '';
                    if (!this.noTranslations) {
                        this.errorMessage = '';
                    }
                    this.successMessage = '';
                }
            },
            immediate: true
        }
    },
    mounted() {
        this.setDefaultSelection();
        this.checkTranslationHistory();
    }
});