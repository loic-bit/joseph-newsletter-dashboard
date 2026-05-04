// Joseph Khateri Newsletter — Claude content generation function
// Deployed as a Netlify serverless function. API key lives in Netlify env vars only.

const HAIKU  = 'claude-haiku-4-5-20251001';
const SONNET = 'claude-sonnet-4-6';

const JOSEPH_SYSTEM = `You are a content strategist for "Investing Section 8" — Joseph Khateri's Section 8 real estate mentorship.

AUDIENCE (ICP): Mid-30s to 50s W2 professionals (engineers, teachers, contractors, small business owners). Live in expensive markets (CA, NY, NJ, WA, DC). Have $20K-$100K saved. Been researching Section 8 for months or years. Never pulled the trigger. Analysis paralysis. Scared of making a $10-15K mistake alone.

Top fears: bad tenants destroying property | picking the wrong market | wasting their savings | getting scammed by a guru
Top desires: passive income depositing while they sleep | stop trading time for money | financial security | generational wealth

OFFER: Done-with-you Section 8 mentorship. 6-month program ($4K) or 12-month program ($6K). Guarantee: first profitable property in that window or Joseph keeps working for free. Includes: 1-on-1 with Joseph directly (his personal number), DealFinder AI (proprietary daily deal feed), vetted team in the right markets, weekly group calls.

JOSEPH: Licensed realtor in Virginia (legal obligation to tell the truth — no guru has this). Built $2.4M Section 8 portfolio by age 21. $30K/month gross. Started at 18 with $0 and no connections. First deal was a disaster (failed HUD inspections, burglarized, lost $6K). That pain built his system. 70+ clients, 100+ Section 8 properties acquired.

PROVEN RESULTS (use these, never fabricate):
- Yasir Tariq: data analyst, GA, 4 properties in Birmingham+Cleveland, $3,700/mo, 6 months, while working full-time
- Daniel Bier: 26, Orange County CA, $76K Detroit purchase, $1,120/mo Section 8 rent, 17.53% cash-on-cash ROI, 4 months
- Sarah: teacher in California, 4 Cleveland properties, $3,500/mo, 18 months — never visited her properties
- Marcus: 2 years stuck in research mode, first deal in 6 weeks, $650/mo, now $1,800/mo
- David: $30K saved, first property in 3 months, 19% ROI, now 5 properties at $2,400/mo
- Giorgio: 0 to 9 properties using BRRRR, $14K/mo gross in 5 months

KEY MECHANISMS:
- Government pays 70-100% of rent directly to landlord's account, deposited every month
- DSCR loans: qualify on property income not W2 or tax returns, start with $20K-$25K
- 7 million families on the Section 8 waiting list — vacancy is not a real risk
- Markets: Cleveland, Birmingham, Detroit — $70K-$100K homes, $1,250-$1,450/mo government rent
- 95% of Joseph's clients invest out of state. 70% never visit their properties.
- Honest cash-on-cash returns: 15-25% (never overclaim)

VOICE RULES — NON-NEGOTIABLE:
- NO em dashes (never — and never --)
- NO these words: game-changer, transform, leverage, unlock, streamline, elevate, journey, revolutionary, cutting-edge, empower
- Do NOT open the email body with "I" — open with a scene, a question, or a third-person story
- One idea per sentence, short paragraphs (1-3 sentences max)
- Specific: use market names, dollar amounts, timeframes, percentages — never vague
- Conversational: write like Joseph is texting a serious investor who asked him a direct question
- Proof over claims: show a real result instead of asserting something is "powerful" or "proven"
- Honest: no fake scarcity, no manufactured urgency, no overpromising

You output ONLY valid JSON. No text, no explanation, no markdown — just the JSON object.`;

async function callClaude(model, userPrompt, maxTokens) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY not set in environment');

  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      system: JOSEPH_SYSTEM,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Claude API ${res.status}: ${err}`);
  }

  const data = await res.json();
  return data.content[0].text;
}

function parseJSON(raw) {
  const stripped = raw.replace(/^```(?:json)?\s*/m, '').replace(/\s*```$/m, '').trim();
  try {
    return JSON.parse(stripped);
  } catch {
    const m = stripped.match(/\{[\s\S]*\}/);
    if (m) return JSON.parse(m[0]);
    throw new Error('Could not parse JSON from Claude response');
  }
}

function buildTopicsPrompt(research, previousTopics) {
  const avoidNote = previousTopics && previousTopics.length > 0
    ? `\nThe user already saw these topics and wants different ones — do NOT repeat them:\n${previousTopics.map(t => `- ${t.title}`).join('\n')}\n`
    : '';

  const compact = {
    reddit_questions: research.reddit_questions.slice(0, 10).map(r => ({ source: r.source, text: r.text.slice(0, 200), score: r.score, url: r.url })),
    reddit_top_posts: research.reddit_top_posts.slice(0, 8).map(r => ({ source: r.source, title: r.title, text: (r.text || '').slice(0, 150), score: r.score, url: r.url })),
    youtube_questions: research.youtube_questions.slice(0, 6).map(y => ({ video: y.video_title, text: y.text.slice(0, 200), likes: y.likes })),
    youtube_comments: research.youtube_comments.slice(0, 8).map(y => ({ video: y.video_title, text: y.text.slice(0, 200), likes: y.likes })),
    news_items: research.news_items.slice(0, 12).map(n => ({ title: n.title, source: n.source })),
    student_wins: (research.student_wins || []).slice(0, 5),
  };

  return `Based on this research data, identify 3 distinct newsletter topics with strong signal for Joseph Khateri's audience.${avoidNote}

Rules for topic selection:
1. Cross-source convergence wins: the same fear or theme in YouTube + Reddit + News = strongest signal
2. The topic must address something Joseph's ICP is thinking about RIGHT NOW
3. Make each topic a different type: e.g. myth-busting vs. market insight vs. social proof
4. Every topic must cite a specific source URL or engagement metric

RESEARCH DATA:
${JSON.stringify(compact)}

Return exactly this JSON structure:
{
  "topics": [
    {
      "id": "topic-1",
      "title": "Specific topic title in 8-15 words",
      "source": "Source name + engagement metric (e.g. '6 of 12 news items + YouTube comment')",
      "signal_quote": "Exact quote or close paraphrase from the data that surfaced this topic",
      "hook": "2-3 sentences: why this topic matters RIGHT NOW for Joseph's ICP and what fear or desire it taps",
      "joseph_angle": "1-2 sentences: what Joseph's specific expertise adds that generic real estate advice cannot",
      "icp_fit": "Which specific fear, desire, or objection from Joseph's ICP this addresses",
      "cta": "none",
      "type": "myth_busting"
    },
    { "id": "topic-2", "title": "...", "source": "...", "signal_quote": "...", "hook": "...", "joseph_angle": "...", "icp_fit": "...", "cta": "none or soft", "type": "pure_value or market_insight or social_proof or story" },
    { "id": "topic-3", "title": "...", "source": "...", "signal_quote": "...", "hook": "...", "joseph_angle": "...", "icp_fit": "...", "cta": "none or soft", "type": "..." }
  ]
}`;
}

function buildEmailPrompt(topic, studentWins) {
  const winsText = studentWins.length > 0
    ? studentWins.map(w => `${w.name}: $${w.cash_collected} collected, source: ${w.lead_source || 'direct'}`).join('\n')
    : 'None available for this cycle.';

  return `Generate 3 distinct email newsletter variations for Joseph Khateri on this topic.

TOPIC: ${topic.title}
SOURCE SIGNAL: ${topic.source}
SIGNAL QUOTE: "${topic.signal_quote}"
JOSEPH'S ANGLE: ${topic.joseph_angle}
ICP FIT: ${topic.icp_fit}
CTA TYPE: ${topic.cta}

RECENT STUDENT WINS (use if relevant, never invent):
${winsText}

Email rules:
- Subject line: under 8 words, all lowercase, sounds like a text to a friend not a marketing email
- Preview text: continues or contrasts with the subject line
- Body: 150-300 words. Open with a scene, a question, or a story about a specific person — NEVER start with "I"
- Short paragraphs: 1-3 sentences each
- Include one named student result if it fits naturally
- No em dashes, no hype words
- The 3 versions must use different structural approaches (not just synonym swaps)

Return exactly this JSON:
{
  "email": [
    { "subject": "...", "alt_subject": "...", "preview": "...", "body": "..." },
    { "subject": "...", "alt_subject": "...", "preview": "...", "body": "..." },
    { "subject": "...", "alt_subject": "...", "preview": "...", "body": "..." }
  ]
}`;
}

function buildStoriesPrompt(topic, studentWins) {
  const winsText = studentWins.length > 0
    ? studentWins.map(w => `${w.name}: $${w.cash_collected} collected`).join('\n')
    : 'None available for this cycle.';

  return `Generate 3 distinct Instagram Story sequences for Joseph Khateri on this topic.

TOPIC: ${topic.title}
JOSEPH'S ANGLE: ${topic.joseph_angle}
ICP FIT: ${topic.icp_fit}
CTA TYPE: ${topic.cta}

STUDENT WINS (use if relevant):
${winsText}

Story rules:
- 4-6 slides per sequence
- Under 15 words per slide (this is on-screen text only — the visual carries the rest)
- Structure: Hook → Context → Insight → Proof (if a real win fits) → CTA or Engagement question
- The 3 sequences must have different hooks and different structural angles
- No em dashes, no hype words

Return exactly this JSON:
{
  "stories": [
    { "slides": [{ "label": "Hook", "text": "..." }, { "label": "Context", "text": "..." }, { "label": "Insight", "text": "..." }, { "label": "CTA", "text": "..." }] },
    { "slides": [...] },
    { "slides": [...] }
  ]
}`;
}

function buildSkoolPrompt(topic) {
  return `Generate 3 distinct Skool free community post variations for Joseph Khateri on this topic.

TOPIC: ${topic.title}
JOSEPH'S ANGLE: ${topic.joseph_angle}

Skool post rules:
- Under 200 words
- Conversational, community-first tone (these people already follow Joseph and trust him)
- Start with a specific hook: a question, a stat, or a short scene
- Deliver one piece of genuine value
- End with an engagement question or light CTA ("drop a comment", "DM me", etc.)
- No hard sell, no fake urgency
- The 3 variations must have different openers and different angles

Return exactly this JSON:
{
  "skool": [
    { "body": "..." },
    { "body": "..." },
    { "body": "..." }
  ]
}`;
}

exports.handler = async (event) => {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON body' }) };
  }

  const { action, research, topic, previous_topics } = body;

  try {
    if (action === 'generate_topics') {
      const prompt = buildTopicsPrompt(research, previous_topics || []);
      const raw = await callClaude(HAIKU, prompt, 2500);
      const parsed = parseJSON(raw);
      return { statusCode: 200, headers, body: JSON.stringify(parsed) };
    }

    if (action === 'generate_content') {
      if (!topic) return { statusCode: 400, headers, body: JSON.stringify({ error: 'topic required' }) };

      const studentWins = (research.student_wins || []);

      const [emailRaw, storiesRaw, skoolRaw] = await Promise.all([
        callClaude(SONNET, buildEmailPrompt(topic, studentWins), 5000),
        callClaude(HAIKU,  buildStoriesPrompt(topic, studentWins), 2500),
        callClaude(HAIKU,  buildSkoolPrompt(topic), 2000),
      ]);

      const result = {
        ...parseJSON(emailRaw),
        ...parseJSON(storiesRaw),
        ...parseJSON(skoolRaw),
      };

      return { statusCode: 200, headers, body: JSON.stringify(result) };
    }

    return { statusCode: 400, headers, body: JSON.stringify({ error: `Unknown action: ${action}` }) };

  } catch (err) {
    console.error('generate error:', err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};
