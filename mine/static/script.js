document.addEventListener('DOMContentLoaded', async (event) => {
    const formToJSON = form => Object.fromEntries(new FormData(form))
    const nickname = document.body.dataset.nickname

    console.log("Connecting to socketio backend")
    const socket = io()
    socket.on('connect', () => {
        console.log("connected")
        socket.emit('connect-ack', {messages: `${nickname} is connected`})
    })
    socket.on(nickname, (data) => {
        message = JSON.parse(data)
        const newRow = document.createElement("div")
        newRow.innerHTML = `[from: ${message.author.nickname}, to : ${message.recipient.nickname}, on ${message.date}]: &OpenCurlyDoubleQuote; ${ message.content } &CloseCurlyDoubleQuote;`
        document.getElementById("messages").appendChild(newRow);
    })

    document.getElementById('send-form').addEventListener('submit',
        async (event) => {
            // turn off default form behaviour
            event.preventDefault()
            const json = formToJSON(event.target)
            const action = event.target.action
            await fetch(action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(json)
            })
        })
    })