new Vue({
    el: '#app',
    delimiters: ['${', '}'],
    data: {
        availableLanguages: [],
        availableLanguageGroups: [],
        selectedLanguage: '',
        minDateTime: '',
        successMessage: '',
        errorMessage: ''
    },
    computed: {
        selectedLanguageId() {
            if (!this.selectedLanguage) return null;
            return this.selectedLanguage.id || this.selectedLanguage.google_code;
        }
    },
    methods: {
        loadAvailableOptions() {
            fetch('{% url "words_export_options" %}')
                .then(response => response.json())
                .then(data => {
                    this.availableLanguages = data.languages;
                    this.availableLanguageGroups = data.language_groups;
                })
                .catch(error => {
                    this.errorMessage = 'Error loading options: ' + error.message;
                });
        },
        updateMinDateTime() {
            console.log('Updating min date time for:', this.selectedLanguageId);
            if (!this.selectedLanguageId) {
                this.minDateTime = '';
                return;
            }

            this.errorMessage = ''; // Clear any previous error message

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
                    this.minDateTime = data.last_export_datetime || '';
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

            fetch('{% url "export_words" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({
                    language: this.selectedLanguageId,
                    min_datetime: this.minDateTime
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.successMessage = 'Words exported successfully!';
                    this.errorMessage = '';
                } else {
                    this.errorMessage = data.error || 'An error occurred during export.';
                    this.successMessage = '';
                }
            })
            .catch(error => {
                this.errorMessage = 'Error exporting words: ' + error.message;
                this.successMessage = '';
            });
        }
    },
    watch: {
        selectedLanguage: {
            handler(newVal) {
                if (newVal) {
                    this.updateMinDateTime();
                } else {
                    this.minDateTime = '';
                    this.errorMessage = '';
                }
            },
            immediate: true
        }
    },
    mounted() {
        this.loadAvailableOptions();
    }
});