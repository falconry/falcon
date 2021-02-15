class EventReceiver {
    constructor(endpoint, containerId) {
        this.source = new EventSource(endpoint);
        this.source.onmessage = this.receiveEvent.bind(this);
        this.containerId = containerId;
    }

    receiveEvent(event) {
        let newElement = document.createElement('div');
        newElement.classList.add('message');
        newElement.classList.add('sse');
        newElement.textContent = event.data;

        let messages = document.getElementById(this.containerId);
        messages.appendChild(newElement);
    }
}


var receiver = new EventReceiver('/sse', 'messages');
