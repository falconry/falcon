class EventReceiver {
    constructor(endpoint, messagesId) {
        this.source = new EventSource(endpoint);
        this.source.onmessage = this.receiveEvent.bind(this);
        this.messagesId = messagesId;
    }

    receiveEvent(event) {
        let newElement = document.createElement('div');
        newElement.classList.add('message');
        newElement.classList.add('sse');
        newElement.textContent = event.data;

        let messages = document.getElementById(this.messagesId);
        messages.appendChild(newElement);
    }
}


class ChatSocket {
    constructor(endpoint, cls, inputId, buttonId, messagesId) {
        this.endpoint = endpoint;
        this.cls = cls;
        this.inputId = inputId;
        this.buttonId = buttonId;
        this.messagesId = messagesId;
        this.socket = null;

        let button = document.getElementById(buttonId);
        button.onclick = this.connect.bind(this);
    }

    connect() {
        let uri = 'ws://' + window.location.host + this.endpoint;
        this.socket = new WebSocket(uri);
        this.socket.onopen = this.onOpen.bind(this);
        this.socket.onmessage = this.onMessage.bind(this);
        this.socket.onclose = this.onClose.bind(this);
    }

    send() {
        let input = document.getElementById(this.inputId);
        this.socket.send(input.value);
        input.value = '';
    }

    appendMessage(message) {
        let newElement = document.createElement('div');
        newElement.classList.add('message');
        newElement.classList.add(this.cls);
        newElement.textContent = message;

        let messages = document.getElementById(this.messagesId);
        messages.appendChild(newElement);
    }

    onOpen(event) {
        let button = document.getElementById(this.buttonId);
        button.innerText = button.innerText.replace('Connect', 'Send');
        button.onclick = this.send.bind(this);

        let input = document.getElementById(this.inputId);
        input.disabled = false;
    }

    onMessage(event) {
        this.appendMessage(event.data);
    }

    onClose(event) {
        document.getElementById(this.buttonId).disabled = true;

        let input = document.getElementById(this.inputId);
        input.disabled = true;
        input.value = `DISCONNECTED (${event.code} ${event.reason})`;
    }
}


var receiver = new EventReceiver('/sse', 'messages');
var ws1 = new ChatSocket('/ws/WS1', 'ws1', 'input1', 'button1', 'messages');
var ws2 = new ChatSocket('/ws/WS2', 'ws2', 'input2', 'button2', 'messages');
