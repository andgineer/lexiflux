new Vue({
    el: '#ai-keys',
    delimiters: ['[[', ']]'],
    data: function() {
        const keys = JSON.parse(document.getElementById('ai-keys-data').textContent);
        return {
            keys: keys,
            inputs: Object.fromEntries(keys.map(key => [key.ref, ''])),
            busy: Object.fromEntries(keys.map(key => [key.ref, false])),
            errorMessage: '',
        };
    },
    computed: {
        sections() {
            return [
                {
                    title: 'Free pool',
                    note: 'Any one of these free keys is enough for the free pool; more keys make it faster and steadier.',
                    keys: this.keys.filter(key => key.pool),
                },
                {
                    title: 'Paid models',
                    note: 'Each paid model needs its provider\'s key.',
                    keys: this.keys.filter(key => !key.pool),
                },
            ].filter(section => section.keys.length);
        },
    },
    methods: {
        sourceText(key) {
            if (key.source === 'own') return key.last4 ? 'Your key …' + key.last4 : 'Your key';
            if (key.source === 'server') return "Server's key";
            return 'Not set';
        },
        sourceClass(key) {
            if (key.source === 'own') return 'text-bg-success';
            if (key.source === 'server') return 'text-bg-info';
            return 'text-bg-secondary';
        },
        send(key, method, body) {
            this.$set(this.busy, key.ref, true);
            this.errorMessage = '';
            return fetch('{% url "ai_key_api" "REF" %}'.replace('REF', encodeURIComponent(key.ref)), {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}',
                },
                body: body === undefined ? undefined : JSON.stringify(body),
            })
            .then(response => {
                // The login page after a session ends, or Django's CSRF page, comes back as HTML.
                if (!(response.headers.get('Content-Type') || '').includes('application/json')) {
                    throw new Error(response.redirected || response.ok
                        ?'Your session has ended. Reload the page, sign in and try again.'
                        : 'The server refused the request (' + response.status + '). Reload the page and try again.');
                }
                return response.json().then(data => {
                    if (!response.ok) throw new Error(data.error || response.statusText);
                    return data;
                });
            })
            .then(data => {
                const index = this.keys.findIndex(item => item.ref === key.ref);
                this.$set(this.keys, index, data.key);
                this.$set(this.inputs, key.ref, '');
            })
            .catch(error => {
                this.errorMessage = key.name + ': ' + error.message;
            })
            .finally(() => {
                this.$set(this.busy, key.ref, false);
            });
        },
        save(key) {
            const value = (this.inputs[key.ref] || '').trim();
            if (!value) return;
            this.send(key, 'POST', {key: value});
        },
        clear(key) {
            this.send(key, 'DELETE');
        },
    },
});
