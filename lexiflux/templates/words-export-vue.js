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
        isExporting: false
    },
    computed: {
        selectedLanguageId() {
            if (!this.selectedLanguage) return null;
            return this.selectedLanguage.id || this.selectedLanguage.google_code;
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

            this.errorMessage = ''; // Clear any previous error message
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

            this.errorMessage = '';
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
                if (this.exportMethod === 'ankiFile') {
                    if (response.ok) {
                        // For file downloads, we need to create a blob and trigger the download
                        return response.blob().then(blob => {
                             const filename = response.headers.get('Content-Disposition').split('filename=')[1].replace(/"/g, '');
                             this.saveFile(blob, filename);                        });
                    } else {
                        return response.json().then(data => {
                            throw new Error(data.error || 'An error occurred during export.');
                        });
                    }
                } else {
                    return response.json();
                }
            })
            .then(data => {
                if (this.exportMethod !== 'ankiFile') {
                    if (data.status === 'success') {
                        this.successMessage = `Words exported successfully! ${data.exported_words} words exported.`;
                    } else {
                        this.errorMessage = data.error || 'An error occurred during export.';
                    }
                }
            })
            .catch(error => {
                this.isExporting = false;
                this.errorMessage = 'Error exporting words: ' + error.message;
            });
        },
        async saveFile(blob, suggestedName) {
            if ('showSaveFilePicker' in window) {
                try {
                    const handle = await window.showSaveFilePicker({
                        suggestedName: suggestedName,
                        types: [{
                            description: 'CSV File',
                            accept: {'text/csv': ['.csv']},
                        }],
                    });
                    const writable = await handle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    this.successMessage = `File "${suggestedName}" has been saved successfully.`;
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        console.error('Failed to save the file:', err);
                        this.errorMessage = 'Failed to save the file. ' + err.message;
                    }
                }
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
                this.successMessage = `File "${suggestedName}" has been downloaded successfully.`;
            }
        },
    },
    watch: {
        selectedLanguage: {
            handler(newVal) {
                if (newVal) {
                    this.updateMinDateTime();
                } else {
                    this.minDateTime = '';
                    this.errorMessage = '';
                    this.successMessage = '';
                }
            },
            immediate: true
        }
    },
    mounted() {
        this.setDefaultSelection();
    }
});