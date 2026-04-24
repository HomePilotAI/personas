const express = require('express');
const { tools } = require('./tools');

const app = express();
app.use(express.json({ limit: '1mb' }));

const ALLOWED_VIBES = [
  'teasing',
  'playful',
  'romantic',
  'mysterious',
  'cinematic',
  'comedic',
  'dramatic',
  'cozy',
  'high-energy'
];

const EXAMPLE_IDEAS = [
  'teach beginners basic Spanish conversation practice',
  'walk new sales reps through our 3 pricing tiers with quizzes',
  'explain photosynthesis with a short branching story',
  'compliance onboarding for a new hire — 4 decisions, 3 endings'
];

function pick(arr, indexSeed) {
  return arr[Math.abs(indexSeed) % arr.length];
}

function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

function normalizeVibe(vibe) {
  if (!vibe) return 'playful';
  const requested = String(vibe).trim().toLowerCase();
  return ALLOWED_VIBES.includes(requested) ? requested : 'playful';
}

function buildSessionVibe({ persona = 'Lina', vibe = 'playful', idea = '' }) {
  const normalizedVibe = normalizeVibe(vibe);
  const ideaText = idea ? ` Theme: ${idea}.` : '';
  return {
    persona,
    vibe: normalizedVibe,
    short_prompt: `${normalizedVibe} ${persona} live-play session with flirty tension, clear stakes, and escalating choices.${ideaText}`.trim(),
    notes: [
      'Keep prompts short and visual so video clips stay coherent.',
      'Each branch should reveal personality, not just information.',
      'Escalate emotional stakes across choices to improve retention.'
    ]
  };
}

function buildBranchingProject({
  persona = 'Lina',
  companion = '',
  idea = '',
  vibe = 'playful',
  render_mode = 'video',
  scene_count = 4
}) {
  const safeSceneCount = Number.isInteger(scene_count)
    ? Math.max(3, Math.min(scene_count, 6))
    : 4;
  const normalizedVibe = normalizeVibe(vibe);
  const projectId = `liveplay-${slugify(persona)}-${Date.now().toString().slice(-6)}`;

  const scenes = Array.from({ length: safeSceneCount }, (_, i) => {
    const sceneNumber = i + 1;
    const focus =
      sceneNumber === 1
        ? 'hook'
        : sceneNumber === safeSceneCount
          ? 'resolution'
          : 'decision';

    return {
      id: `scene_${sceneNumber}`,
      title: `${persona} ${focus} ${sceneNumber}`,
      purpose:
        focus === 'hook'
          ? `Open with ${persona}'s core charm and establish the user's goal.`
          : focus === 'resolution'
            ? 'Resolve consequences and route to one of the endings.'
            : `Present branching choice ${sceneNumber - 1} with emotional tradeoffs.`,
      video_prompt: `${normalizedVibe} tone, ${persona} in focus${
        companion ? ` with ${companion}` : ''
      }, cinematic framing, crisp dialogue beats.`,
      choices:
        focus === 'resolution'
          ? []
          : [
              {
                id: `scene_${sceneNumber}_choice_a`,
                label: 'Lean in',
                outcome: 'Increases intimacy and narrative risk.'
              },
              {
                id: `scene_${sceneNumber}_choice_b`,
                label: 'Play it safe',
                outcome: 'Keeps trust high but reduces dramatic payoff.'
              }
            ]
    };
  });

  return {
    project_id: projectId,
    mode: 'persona-live-play',
    persona,
    companion: companion || null,
    render_media: render_mode === 'image' ? 'image' : 'video',
    idea: idea || pick(EXAMPLE_IDEAS, persona.length),
    vibe_prompt: buildSessionVibe({ persona, vibe: normalizedVibe, idea }).short_prompt,
    format: {
      type: 'branching-ai-video',
      has_scenes: true,
      has_choices: true,
      has_endings: true
    },
    scenes,
    endings: [
      { id: 'ending_growth', title: 'Growth Arc', summary: 'User unlocks confident mastery.' },
      { id: 'ending_balance', title: 'Balanced Arc', summary: 'User succeeds with stable trust.' },
      { id: 'ending_chaos', title: 'Chaos Arc', summary: 'Bold risks create a memorable twist.' }
    ],
    production_readiness: {
      status: 'ready-for-production',
      checks: [
        'Scene-to-choice continuity included',
        '3 unique endings provided',
        'Video prompts are concise and reusable',
        'Supports fast image mode fallback'
      ]
    }
  };
}

app.get('/health', (req, res) =>
  res.json({
    status: 'ok',
    server: 'mcp-storyteller',
    timestamp: new Date().toISOString()
  })
);

app.get('/tools', (req, res) => res.json({ tools }));

app.post('/describe_session_vibe', (req, res) => {
  const payload = req.body || {};
  res.json({ result: buildSessionVibe(payload) });
});

app.post('/build_branching_video_project', (req, res) => {
  const payload = req.body || {};
  res.json({ result: buildBranchingProject(payload) });
});

app.post('/suggest_live_play_examples', (req, res) => {
  res.json({
    result: {
      examples: EXAMPLE_IDEAS,
      guidance: 'Choose a concrete audience and a measurable outcome for best branching quality.'
    }
  });
});

// Backward-compatible endpoint from v1.
app.post('/generate_story', (req, res) => {
  const payload = req.body || {};
  const persona = payload.persona || 'Lina';
  const idea = payload.prompt || payload.idea || pick(EXAMPLE_IDEAS, 0);

  res.json({
    result: {
      message:
        'The generate_story endpoint is deprecated. Use /build_branching_video_project for production workflows.',
      project: buildBranchingProject({ persona, idea, vibe: payload.vibe || 'playful' })
    }
  });
});

const port = process.env.PORT || 9107;
app.listen(port, () => console.log(`Server listening on port ${port}`));
