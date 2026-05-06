import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = API.replace(/^http/, 'ws') + '/ws';

function App() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [email, setEmail] = useState('user@localhost');
  const [details, setDetails] = useState(null);
  const [message, setMessage] = useState('');
  const [socketStatus, setSocketStatus] = useState('Подключение...');

  async function loadTasks() {
    const response = await fetch(`${API}/tasks`);
    setTasks(await response.json());
  }

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      setSocketStatus('WebSocket подключён');
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'task_created') {
        setMessage(`Real-time: добавлена задача #${data.task.id}`);
        loadTasks();
      }

      if (data.type === 'task_updated') {
        setMessage(`Real-time: изменена задача #${data.task.id}`);
        loadTasks();
      }

      if (data.type === 'task_deleted') {
        setMessage(`Real-time: удалена задача #${data.task.id}`);
        loadTasks();
      }
    };

    socket.onerror = () => {
      setSocketStatus('Ошибка WebSocket');
    };

    socket.onclose = () => {
      setSocketStatus('WebSocket отключён');
    };

    return () => socket.close();
  }, []);

  async function saveTask(event) {
    event.preventDefault();

    if (editingId) {
      const oldTask = tasks.find((task) => task.id === editingId);
      await fetch(`${API}/tasks/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, completed: oldTask.completed })
      });
    } else {
      await fetch(`${API}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description })
      });
    }

    setTitle('');
    setDescription('');
    setEditingId(null);
    loadTasks();
  }

  async function removeTask(id) {
    await fetch(`${API}/tasks/${id}`, { method: 'DELETE' });
    loadTasks();
  }

  async function toggleTask(task) {
    await fetch(`${API}/tasks/${task.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...task, completed: !task.completed })
    });
    loadTasks();
  }

  async function showDetails(id) {
    const response = await fetch(`${API}/tasks/${id}`);
    setDetails(await response.json());
  }

  async function sendEmail(id) {
    const response = await fetch(`${API}/tasks/${id}/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to: email })
    });
    const data = await response.json();
    setMessage(data.message || data.error || 'Готово');
  }

  async function checkMail(protocol) {
    const response = await fetch(`${API}/mail/${protocol}/check?email=${encodeURIComponent(email)}`);
    setMessage(JSON.stringify(await response.json()));
  }

  function startEdit(task) {
    setEditingId(task.id);
    setTitle(task.title);
    setDescription(task.description || '');
  }

  return (
    <main>
      <h1>ToDo List</h1>
      <p className="socket-status">{socketStatus}</p>

      <form onSubmit={saveTask} className="card">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Название задачи"
          required
        />
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Описание"
        />
        <button>{editingId ? 'Сохранить изменения' : 'Добавить задачу'}</button>
      </form>

      <section className="card">
        <h2>Почта</h2>
        <input
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="email получателя"
        />
        <button onClick={() => checkMail('imap')}>Проверить IMAP</button>
        <button onClick={() => checkMail('pop3')}>Проверить POP3</button>
        <p>{message}</p>
      </section>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Задача</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td>{task.id}</td>
              <td><b>{task.title}</b><br />{task.description}</td>
              <td>{task.completed ? 'Выполнена' : 'Активна'}</td>
              <td>
                <button onClick={() => toggleTask(task)}>Статус</button>
                <button onClick={() => showDetails(task.id)}>Детали</button>
                <button onClick={() => startEdit(task)}>Редактировать</button>
                <button onClick={() => sendEmail(task.id)}>E-mail</button>
                <button className="danger" onClick={() => removeTask(task.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {details && (
        <section className="card details">
          <h2>Детальный просмотр задачи #{details.id}</h2>
          <p><b>Название:</b> {details.title}</p>
          <p><b>Описание:</b> {details.description || '-'}</p>
          <p><b>Статус:</b> {details.completed ? 'Выполнена' : 'Не выполнена'}</p>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
