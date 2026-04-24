const express = require('express');
const tools = require('./tools').tools;
const app = express();
app.use(express.json());
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/tools', (req, res) => res.json({ tools }));
app.post('/suggest_room_decor', (req, res) => res.json({ result: 'Tool suggest_room_decor is not implemented yet.' }));
const port = process.env.PORT || 9106;
app.listen(port, () => console.log(`Server listening on port ${port}`));
