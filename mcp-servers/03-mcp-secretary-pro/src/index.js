const express = require('express');
const tools = require('./tools').tools;
const app = express();
app.use(express.json());
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/tools', (req, res) => res.json({ tools }));
app.post('/manage_schedule', (req, res) => res.json({ result: 'Tool manage_schedule is not implemented yet.' }));
const port = process.env.PORT || 9103;
app.listen(port, () => console.log(`Server listening on port ${port}`));
