(function() {
    const widget = document.querySelector('[data-chatbot-widget]');
    if (!widget) {
        return;
    }

    const config = window.emgAssistantConfig || {};
    const launcher = widget.querySelector('[data-chatbot-launcher]');
    const panel = widget.querySelector('[data-chatbot-panel]');
    const closeButton = widget.querySelector('[data-chatbot-close]');
    const messages = widget.querySelector('[data-chatbot-messages]');
    const quickPrompts = widget.querySelectorAll('[data-chatbot-prompt]');
    const form = widget.querySelector('[data-chatbot-form]');
    const input = widget.querySelector('[data-chatbot-input]');
    const voiceButton = widget.querySelector('[data-chatbot-voice]');
    const voiceToggle = widget.querySelector('[data-chatbot-speak-toggle]');
    const status = widget.querySelector('[data-chatbot-status]');

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const speechSupported = 'speechSynthesis' in window;
    let recognition = null;
    let voiceRepliesEnabled = speechSupported;
    let isListening = false;

    if (voiceToggle) {
        voiceToggle.textContent = speechSupported ? 'Voice replies: On' : 'Voice replies: Not supported';
        voiceToggle.disabled = !speechSupported;
    }

    function setStatus(text) {
        if (status) {
            status.textContent = text;
        }
    }

    function openPanel() {
        panel.classList.add('is-open');
        panel.setAttribute('aria-hidden', 'false');
        launcher.setAttribute('aria-expanded', 'true');
        window.setTimeout(function() {
            input.focus();
        }, 120);
    }

    function closePanel() {
        panel.classList.remove('is-open');
        panel.setAttribute('aria-hidden', 'true');
        launcher.setAttribute('aria-expanded', 'false');
        if (recognition && isListening) {
            recognition.stop();
        }
    }

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function createAction(action) {
        const link = document.createElement('a');
        link.className = 'chatbot-action';
        link.href = action.url;
        link.textContent = action.label;
        return link;
    }

    function addMessage(role, text, actions) {
        const item = document.createElement('div');
        item.className = 'chatbot-message chatbot-message--' + role;

        const bubble = document.createElement('div');
        bubble.className = 'chatbot-message__bubble';
        bubble.textContent = text;
        item.appendChild(bubble);

        if (actions && actions.length) {
            const actionRow = document.createElement('div');
            actionRow.className = 'chatbot-message__actions';
            actions.forEach(function(action) {
                actionRow.appendChild(createAction(action));
            });
            item.appendChild(actionRow);
        }

        messages.appendChild(item);
        scrollToBottom();
    }

    function speak(text) {
        if (!voiceRepliesEnabled || !speechSupported || !text) {
            return;
        }

        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.lang = 'en-US';
        window.speechSynthesis.speak(utterance);
    }

    function buildDefaultResponse() {
        return {
            text: 'I can help with payments, product search, delivery, account guidance, and order tracking. Try asking about MTN MoMo, Airtel Money, categories, or checkout.',
            actions: [
                { label: 'Products', url: config.routes.products },
                { label: 'Track Order', url: config.routes.tracking },
                { label: 'Contact Support', url: config.routes.contact },
            ],
        };
    }

    function getResponse(message) {
        const text = message.toLowerCase();
        const contains = function(keywords) {
            return keywords.some(function(keyword) {
                return text.includes(keyword);
            });
        };

        if (contains(['mtn', 'momo', 'mobile money'])) {
            return {
                text: 'To pay with MTN MoMo, place your order first, open MTN MoMo on your phone, choose send money or pay merchant, enter the payment details from EMG support, use the exact order total, and save the confirmation SMS with your order number.',
                actions: [
                    { label: 'Go to Checkout', url: config.routes.checkout },
                    { label: 'Call Support', url: 'tel:' + config.supportPhone },
                    { label: 'WhatsApp Help', url: config.supportWhatsApp },
                ],
            };
        }

        if (contains(['airtel', 'airtel money'])) {
            return {
                text: 'For Airtel Money, place the order first, open Airtel Money on your phone, choose send money or pay merchant, enter the EMG payment details, confirm the exact total, and keep the confirmation message until your delivery is completed.',
                actions: [
                    { label: 'Checkout', url: config.routes.checkout },
                    { label: 'Call Support', url: 'tel:' + config.supportPhone },
                ],
            };
        }

        if (contains(['cash on delivery', 'cash', 'pay on arrival'])) {
            return {
                text: 'Cash on Delivery lets you place the order now and pay when the rider arrives. Keep your order total ready and use the tracking page to monitor the delivery.',
                actions: [
                    { label: 'Checkout', url: config.routes.checkout },
                    { label: 'Track Orders', url: config.routes.tracking },
                ],
            };
        }

        if (contains(['category', 'categories', 'search by category', 'filter'])) {
            return {
                text: 'On the products page you can search by name and also filter by category. Use the category chips or the category dropdown to narrow the catalog quickly.',
                actions: [
                    { label: 'Open Products', url: config.routes.products },
                ],
            };
        }

        if (contains(['name search', 'search by name', 'find product', 'search product'])) {
            return {
                text: 'Use the main search bar on the products page. It supports product names, descriptions, and SKU, and it also gives name suggestions while you type.',
                actions: [
                    { label: 'Search Products', url: config.routes.products },
                ],
            };
        }

        if (contains(['best product', 'best products', 'good products', 'suggestion', 'recommend'])) {
            return {
                text: 'The products page now highlights Best Products and Good Value Picks. Those sections help customers find strong in-stock choices before browsing the full catalog.',
                actions: [
                    { label: 'View Best Products', url: config.routes.products },
                ],
            };
        }

        if (contains(['track', 'tracking', 'where is my order'])) {
            return {
                text: 'Use the tracking page to search with your tracking number, or open My Orders after login to follow a specific order step by step.',
                actions: [
                    { label: 'Track Order', url: config.routes.tracking },
                    { label: 'My Profile', url: config.routes.profile },
                ],
            };
        }

        if (contains(['delivery', 'how long', 'when will it arrive', 'shipping'])) {
            return {
                text: 'EMG Shipping targets delivery across Kigali within 24 hours for most orders. Your tracking page shows the current status and estimated delivery timing.',
                actions: [
                    { label: 'Track Order', url: config.routes.tracking },
                    { label: 'Products', url: config.routes.products },
                ],
            };
        }

        if (contains(['checkout', 'order', 'place order'])) {
            return {
                text: 'To place an order, add products to cart, open checkout, fill in delivery details, choose a payment method, then follow the payment guide shown on the checkout page.',
                actions: [
                    { label: 'Cart', url: config.routes.cart },
                    { label: 'Checkout', url: config.routes.checkout },
                ],
            };
        }

        if (contains(['account', 'profile', 'login', 'register'])) {
            return {
                text: 'You can use the profile menu at the top right to open your profile, see your orders, or log out. New users can register and returning users can log in to manage orders faster.',
                actions: [
                    { label: 'My Profile', url: config.routes.profile },
                ],
            };
        }

        if (contains(['contact', 'support', 'help line', 'phone'])) {
            return {
                text: 'You can contact EMG support on ' + config.supportPhoneDisplay + ' for payment help, delivery questions, and account guidance.',
                actions: [
                    { label: 'Call Support', url: 'tel:' + config.supportPhone },
                    { label: 'WhatsApp', url: config.supportWhatsApp },
                    { label: 'Contact Page', url: config.routes.contact },
                ],
            };
        }

        if (contains(['category list', 'what categories'])) {
            return {
                text: 'Current browsing categories include ' + (config.categories || []).join(', ') + '.',
                actions: [
                    { label: 'Products', url: config.routes.products },
                ],
            };
        }

        return buildDefaultResponse();
    }

    function respond(message) {
        if (!message) {
            return;
        }

        addMessage('user', message);
        const response = getResponse(message);
        addMessage('assistant', response.text, response.actions);
        speak(response.text);
    }

    function submitMessage(event) {
        event.preventDefault();
        const value = input.value.trim();
        if (!value) {
            return;
        }

        input.value = '';
        respond(value);
    }

    function toggleVoiceReplies() {
        voiceRepliesEnabled = !voiceRepliesEnabled;
        voiceToggle.textContent = 'Voice replies: ' + (voiceRepliesEnabled ? 'On' : 'Off');
        setStatus(voiceRepliesEnabled ? 'Voice replies are enabled.' : 'Voice replies are muted.');
        if (!voiceRepliesEnabled && speechSupported) {
            window.speechSynthesis.cancel();
        }
    }

    function setupRecognition() {
        if (!SpeechRecognition) {
            voiceButton.disabled = true;
            voiceButton.classList.add('is-disabled');
            setStatus('Voice input is not supported in this browser, but text chat is ready.');
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.addEventListener('start', function() {
            isListening = true;
            voiceButton.classList.add('is-listening');
            setStatus('Listening for your question...');
        });

        recognition.addEventListener('result', function(event) {
            const transcript = event.results[0][0].transcript;
            input.value = transcript;
            respond(transcript);
        });

        recognition.addEventListener('end', function() {
            isListening = false;
            voiceButton.classList.remove('is-listening');
            setStatus('Ready to help with shopping, payments, and tracking.');
        });

        recognition.addEventListener('error', function() {
            isListening = false;
            voiceButton.classList.remove('is-listening');
            setStatus('Voice input had a problem. You can still type your question.');
        });

        voiceButton.addEventListener('click', function() {
            if (isListening) {
                recognition.stop();
                return;
            }
            recognition.start();
        });
    }

    launcher.addEventListener('click', function() {
        if (panel.classList.contains('is-open')) {
            closePanel();
        } else {
            openPanel();
        }
    });

    closeButton.addEventListener('click', closePanel);
    form.addEventListener('submit', submitMessage);
    voiceToggle.addEventListener('click', toggleVoiceReplies);

    quickPrompts.forEach(function(button) {
        button.addEventListener('click', function() {
            const prompt = this.dataset.chatbotPrompt;
            respond(prompt);
            openPanel();
        });
    });

    addMessage(
        'assistant',
        'Hello. I can guide you through product search, category browsing, MTN MoMo, Airtel Money, checkout, tracking, and general app use.',
        [
            { label: 'Products', url: config.routes.products },
            { label: 'Checkout', url: config.routes.checkout },
        ]
    );

    setupRecognition();
})();
