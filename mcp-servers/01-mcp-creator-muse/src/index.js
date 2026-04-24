const express = require('express');
const tools = require('./tools').tools;
const app = express();
app.use(express.json());
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/tools', (req, res) => res.json({ tools }));
app.post('/creator_muse_inspire', (req, res) => res.json({ result: 'Tool creator_muse_inspire is not implemented yet.' }));
const port = process.env.PORT || 9101;
app.listen(port, () => console.log(`Server listening on port ${port}`));
