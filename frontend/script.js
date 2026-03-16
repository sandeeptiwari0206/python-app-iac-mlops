const BACKEND_URL = "/api";
const output = document.getElementById("output");

function register() {
  fetch(`${BACKEND_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: username.value,
      email: email.value,
      password: password.value
    })
  })
  .then(res => res.json())
  .then(data => showMessage(data.message || JSON.stringify(data)));
}

function createTask() {
  fetch(`${BACKEND_URL}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: title.value,
      description: description.value
    })
  })
  .then(res => res.json())
  .then(data => showMessage(data.message || JSON.stringify(data)));
}

function getUsers() {
  fetch(`${BACKEND_URL}/users`)
    .then(res => res.json())
    .then(users => {
      output.innerHTML = "";
      users.forEach(u => {
        output.innerHTML += `<li class="bg-gray-100 p-2 rounded">
          👤 ${u.username} (${u.email})
        </li>`;
      });
    });
}

function getTasks() {
  fetch(`${BACKEND_URL}/tasks`)
    .then(res => res.json())
    .then(tasks => {
      output.innerHTML = "";
      tasks.forEach(t => {
        output.innerHTML += `<li class="bg-gray-100 p-2 rounded">
          ✅ ${t.title} - ${t.description || ""}
        </li>`;
      });
    });
}

function showMessage(msg) {
  output.innerHTML = `<li class="bg-green-100 p-2 rounded text-green-700">${msg}</li>`;
}

