new Vue({
    el: '#app',
    delimiters: ['${', '}'],
    data: {
        aiConfigs: [],
        originalConfigs: [],
        errorMessage: '',
        successMessage: '',
        changedFields: {},
        errors: {},
        activeTab: '{{ selected_tab }}' || '',
    },
    computed: {
        hasChanges() {
            return Object.keys(this.changedFields).length > 0;
        }
    },
    mounted() {
      if (!this.activeTab && this.aiConfigs.length > 0) {
        this.activeTab = this.aiConfigs[0].chat_model;
      }
    },
    methods: {
        isActiveTab(tabName) {
            return this.activeTab === tabName || (this.activeTab === '' && this.aiConfigs.indexOf(this.aiConfigs.find(config => config.chat_model === tabName)) === 0);
        },
        loadSettings() {
            fetch('{% url "ai_settings_api" %}', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                }
            })
            .then(response => response.json())
            .then(data => {
                this.aiConfigs = data;
                this.originalConfigs = JSON.parse(JSON.stringify(data));
            })
            .catch(error => {
                this.errorMessage = 'Error loading settings: ' + error.message;
            });
        },
        saveSettings() {
            fetch('{% url "ai_settings_api" %}', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify(this.aiConfigs)
            })
            .then(response => {
              if (!response.ok) {
                return response.json().then(err => { throw err; });
              }
              return response.json();
            })
            .then(data => {
              console.log('Settings updated successfully');
              this.errors = {}; // Clear any existing errors
              this.changedFields = {};
            })
            .catch(error => {
              console.error('Error updating settings:', error);
              if (error.errors) {
                this.errors = error.errors;
              } else {
                this.errorMessage = 'Error updating settings: ' + error;
              }
            });
        },
        fieldChanged(chatModel, key) {
            if (!this.changedFields[chatModel]) {
                this.$set(this.changedFields, chatModel, {});
            }
            this.$set(this.changedFields[chatModel], key, true);
        },
        isFieldChanged(chatModel, key) {
            return this.changedFields[chatModel] && this.changedFields[chatModel][key];
        },
        setupBeforeUnloadListener() {
            window.addEventListener('beforeunload', this.handleBeforeUnload);
        },
        teardownBeforeUnloadListener() {
            window.removeEventListener('beforeunload', this.handleBeforeUnload);
        },
        handleBeforeUnload(e) {
            if (this.hasChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        }
    },
    mounted() {
        this.loadSettings();
        this.setupBeforeUnloadListener();
    },
    beforeDestroy() {
        this.teardownBeforeUnloadListener();
    }
});
