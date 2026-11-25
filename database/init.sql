CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    priority VARCHAR(10) DEFAULT 'medium',
    status VARCHAR(10) DEFAULT 'todo',
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO tasks (title, description, priority) VALUES
 ('Préparer la démo Jenkins', 'Pipeline build + deploy', 'high'),
 ('Écrire la documentation', 'README du projet', 'medium');
