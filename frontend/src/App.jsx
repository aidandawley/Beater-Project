import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function Login() {
  return <main className="login-card">
    <div className="badge">⚠️ intentionally vulnerable lab</div>
    <h1>Beater Todo</h1>
    <p>A snazzy little CRUD app with Google auth, SQLite, FastAPI, React, and a Gemini sidekick.</p>
    <a className="google" href={`${API}/auth/google/login`}>Sign in with Google</a>
  </main>;
}

function App() {
  const [user, setUser] = useState(null);
  const [todos, setTodos] = useState([]);
  const [form, setForm] = useState({ title: '', notes: '', priority: 'normal' });
  const [chat, setChat] = useState([{ role: 'bot', text: 'Hey! I am BeaterBot. Ask me how to break your task list into tiny wins.' }]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => { setUser(await api('/me')); setTodos(await api('/todos')); };
  useEffect(() => { load().catch(() => setUser(false)); }, []);

  async function addTodo(event) {
    event.preventDefault();
    const todo = await api('/todos', { method: 'POST', body: JSON.stringify(form) });
    setTodos([todo, ...todos]);
    setForm({ title: '', notes: '', priority: 'normal' });
  }

  async function toggle(todo) {
    const updated = await api(`/todos/${todo.id}`, { method: 'PATCH', body: JSON.stringify({ completed: !todo.completed }) });
    setTodos(todos.map((item) => item.id === todo.id ? updated : item));
  }

  async function remove(todo) {
    await api(`/todos/${todo.id}`, { method: 'DELETE' });
    setTodos(todos.filter((item) => item.id !== todo.id));
  }

  async function sendChat(event) {
    event.preventDefault();
    const next = [...chat, { role: 'user', text: message }];
    setChat(next); setMessage('');
    try {
      const data = await api('/chat', { method: 'POST', body: JSON.stringify({ message }) });
      setChat([...next, { role: 'bot', text: data.reply }]);
    } catch (err) { setError(err.message); }
  }

  if (user === null) return <div className="loading">Loading Beater Todo...</div>;
  if (!user) return <Login />;

  return <div className="shell">
    <section className="panel main-panel">
      <header>
        <div><p className="eyebrow">vibe-coded command center</p><h1>Today's chaos list</h1></div>
        <button onClick={() => api('/auth/logout', { method: 'POST' }).then(() => location.reload())}>↩ Logout</button>
      </header>
      <div className="profile"><img src={user.avatar_url || 'https://www.gravatar.com/avatar/?d=mp'} /><span>{user.name}<small>{user.email}</small></span></div>
      <form className="todo-form" onSubmit={addTodo}>
        <input placeholder="Ship the thing..." value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}/>
        <input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}/>
        <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}><option>low</option><option>normal</option><option>spicy</option></select>
        <button>+ Add</button>
      </form>
      <div className="todos">{todos.map((todo) => <article className={todo.completed ? 'todo done' : 'todo'} key={todo.id}>
        <button className="check" onClick={() => toggle(todo)}>✓</button><div><h3>{todo.title}</h3><p>{todo.notes || 'No notes, just vibes.'}</p><span>{todo.priority}</span></div><button className="danger" onClick={() => remove(todo)}>🗑</button>
      </article>)}</div>
    </section>
    <aside className="panel chat-panel">
      <h2>🤖 BeaterBot ✨</h2>
      <div className="chat-log">{chat.map((line, index) => <div key={index} className={`bubble ${line.role}`} dangerouslySetInnerHTML={{ __html: line.text }} />)}</div>
      {/* SECURITY_TEST_VULN: bot output is rendered as HTML for scanner testing. */}
      <form onSubmit={sendChat}><input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Ask Gemini 1.5 Flash..."/><button>Send</button></form>
      {error && <pre className="error">{error}</pre>}
    </aside>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
