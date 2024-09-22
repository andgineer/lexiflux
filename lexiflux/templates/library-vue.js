new Vue({
    el: '#app',
    delimiters: ['${', '}'],
    data: {
        editedBook: {
            id: null,
            title: '',
            author: '',
            language: ''
        },
        bookCode: '',
        authorSearch: '',
        authorSuggestions: [],
        hasMoreAuthors: false,
        languages: JSON.parse('{{ languages|safe }}'),
        importFile: null,
        errorMessage: '',
        successMessage: '',
        deleteErrorMessage: '',
        searchTimeout: null,
        isNewlyImported: false,
        isImporting: false,
    },
    watch: {
        authorSearch(newValue) {
            this.editedBook.author = newValue;
        }
    },
    methods: {
        showImportModal() {
            this.errorMessage = '';
            new bootstrap.Modal(document.getElementById('importModal')).show();
        },
        handleFileUpload(event) {
            this.importFile = event.target.files[0];
        },
        importBook() {
            this.errorMessage = '';
            if (!this.importFile) {
                this.errorMessage = 'Please select a file to import.';
                return;
            }
            this.isImporting = true;
            let formData = new FormData();
            formData.append('file', this.importFile);

            fetch('/api/import-book/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Import error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                this.isNewlyImported = true;  // Set the flag
                this.editBook(data.id);  // Open edit modal with the new book's ID
                bootstrap.Modal.getInstance(document.getElementById('importModal')).hide();
            })
            .catch(error => {
                console.error('Error:', error);
                this.errorMessage = error.message || 'An error occurred while importing the book.';
            })
            .finally(() => {
                this.isImporting = false;
            });
        },
        editBook(bookId) {
            this.errorMessage = '';
            fetch(`/api/books/${bookId}/`)
                .then(response => response.json())
                .then(data => {
                    this.authorSearch = data.author;
                    this.editedBook = data;
                    this.bookCode = data.code;
                    new bootstrap.Modal(document.getElementById('editBookModal')).show();
                })
                .catch(error => {
                    console.error('Error:', error);
                    this.errorMessage = 'An error occurred while fetching book details.';
                });
        },
        searchAuthors() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                if (this.authorSearch.length < 2) {
                    this.authorSuggestions = [];
                    this.hasMoreAuthors = false;
                    return;
                }
                fetch(`/api/search-authors/?q=${encodeURIComponent(this.authorSearch)}`)
                    .then(response => response.json())
                    .then(data => {
                        this.authorSuggestions = data.authors;
                        this.hasMoreAuthors = data.has_more;
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        this.errorMessage = 'An error occurred while searching for authors.';
                    });
            }, 300);
        },
        selectAuthor(author) {
            this.authorSearch = author;
            this.editedBook.author = author;
            this.authorSuggestions = [];
        },
        saveChanges() {
            this.errorMessage = '';
            fetch(`/api/books/${this.editedBook.id}/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify(this.editedBook)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    this.errorMessage = data.error;
                } else {
                    bootstrap.Modal.getInstance(document.getElementById('editBookModal')).hide();
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.errorMessage = 'An error occurred while updating the book.';
            });
        },
        showDeleteConfirmation() {
            this.deleteErrorMessage = ''; // Clear any previous error message
            if (this.isNewlyImported) {
                // If it's a newly imported book, delete it directly without confirmation
                this.deleteBook();
            } else {
                // For existing books, close the edit modal before showing the confirmation modal
                bootstrap.Modal.getInstance(document.getElementById('editBookModal')).hide();
                this.$nextTick(() => {
                    new bootstrap.Modal(document.getElementById('deleteConfirmationModal')).show();
                });
            }
        },
        deleteBook() {
          fetch(`/api/books/${this.editedBook.id}/`, {
            method: 'DELETE',
            headers: {
              'X-CSRFToken': '{{ csrf_token }}',
            },
          })
          .then(response => {
            if (!response.ok) {
              return response.json().then(data => {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
              });
            }
            return response.json();
          })
          .then(data => {
            if (data.success) {
              location.reload();
            }
          })
          .catch(error => {
            console.error('Error:', error);
            this.deleteErrorMessage = error;
          });
        },
        getProgressWidth(progress) {
          return `${progress}%`;
        },
    }
});