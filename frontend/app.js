const API = '/api';
let tasks = [];
let filter = 'all';
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LABEL = { high: 'Urgente', medium: 'Moyenne', low: 'Faible' };

async function load() {
  const r = await fetch(`${API}/tasks`);
  tasks = await r.json();
  render();
}

function render() {
  $('s-total').textContent = tasks.length;
  $('s-todo').textContent = tasks.filter(t => t.status !== 'done').length;
  $('s-high').textContent = tasks.filter(t => t.priority === 'high' && t.status !== 'done').length;
  $('s-done').textContent = tasks.filter(t => t.status === 'done').length;

  const shown = tasks.filter(t => filter === 'all' || (filter === 'done') === (t.status === 'done'));
  $('list').innerHTML = shown.length ? shown.map(t => `
    <article class="glass task ${t.status === 'done' ? 'done' : ''}">
      <button class="check" onclick="toggle(${t.id})">${t.status === 'done' ? '✓' : ''}</button>
      <div class="info"><h3>${esc(t.title)}</h3>${t.description ? `<p>${esc(t.description)}</p>` : ''}</div>
      <span class="badge ${t.priority}">${LABEL[t.priority] || t.priority}</span>
      <button class="del" onclick="removeTask(${t.id})">🗑</button>
    </article>`).join('') : '<p class="empty">Aucune tâche ici 🎈</p>';
}

async function addTask() {
  const title = $('title').value.trim();
  if (!title) return;
  await fetch(`${API}/tasks`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description: $('desc').value.trim() })
  });
  $('title').value = ''; $('desc').value = '';
  load();
}

async function toggle(id) {
  const t = tasks.find(x => x.id === id);
  await fetch(`${API}/tasks/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: t.status === 'done' ? 'todo' : 'done' })
  });
  load();
}

async function removeTask(id) {
  await fetch(`${API}/tasks/${id}`, { method: 'DELETE' });
  load();
}

async function suggest() {
  $('tips').innerHTML = '<li>🤖 Analyse en cours…</li>';
  try {
    const r = await fetch(`${API}/suggestions`);
    const data = await r.json();
    $('tips').innerHTML = data.suggestions.map(s => `<li>${esc(s)}</li>`).join('');
  } catch { $('tips').innerHTML = '<li>Service IA indisponible.</li>'; }
}

$('add').onclick = addTask;
$('title').addEventListener('keydown', e => e.key === 'Enter' && addTask());
$('suggest').onclick = suggest;
document.querySelectorAll('.chip').forEach(c => c.onclick = () => {
  document.querySelectorAll('.chip').forEach(x => x.classList.remove('active'));
  c.classList.add('active'); filter = c.dataset.f; render();
});
load();
