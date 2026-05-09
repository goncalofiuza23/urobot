import gradio as gr
import json
from tutor_engine import TutorEngine

engine = TutorEngine()

chat_history = []

# ── Helpers ───────────────────────────────────────────────────────────────────

def upload_files(files):
    if not files:
        return build_docs_html()
    for f in files:
        engine.load_document(f.name)
    return build_docs_html()

def build_docs_html():
    info = engine.get_collection_info()
    if not info["files"]:
        return '<div class="empty-docs">Nenhum documento carregado.</div>'
    items = ""
    for f in info["files"]:
        ext = f.split(".")[-1].upper() if "." in f else "DOC"
        items += f'<div class="doc-item"><span class="doc-icon">{ext}</span><span class="doc-name">{f}</span></div>'
    return f'<div class="doc-list">{items}<div class="doc-count">{info["total_docs"]} fragmentos indexados</div></div>'

def chat_send(message, history):
    if not message.strip():
        return history, ""
    history = history or []
    response = engine.ask(message, history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return history, ""

def clear_chat():
    return [], ""

def make_summary(topic):
    if not topic.strip():
        return "Escreve um topico para gerar o resumo."
    return engine.summarize(topic)

def make_quiz(topic, n):
    import json as _json
    if not topic.strip():
        return '<p style="color:#6b7280;font-size:0.84rem">Escreve um topico para gerar o questionario.</p>'
    raw = engine.generate_quiz(topic, int(n))
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return '<p style="color:#ef4444;font-size:0.84rem">O modelo nao gerou um questionario valido. Tenta novamente.</p>'
    raw = raw[start:end+1]
    if raw == "[]":
        return '<p style="color:#ef4444;font-size:0.84rem">Nao encontrei informacao suficiente sobre este topico nos materiais carregados.</p>'
    try:
        questions = _json.loads(raw)
    except Exception:
        return '<p style="color:#ef4444;font-size:0.84rem">Erro ao processar o questionario. Tenta novamente.</p>'

    letters = ["A","B","C","D","E"]
    total = len(questions)
    questions_json = _json.dumps(questions, ensure_ascii=False)

    # Build cards HTML
    cards = ""
    for qi, q in enumerate(questions):
        opts = q.get("options", [])
        cards += f'<div class="card"><div class="qtxt">{qi+1}. {q.get("question","")}</div><div class="opts">'
        for oi, opt in enumerate(opts):
            letter = letters[oi] if oi < len(letters) else str(oi)
            cards += f'<div class="opt" data-qi="{qi}" data-oi="{oi}"><div class="ltr">{letter}</div><span>{opt}</span></div>'
        cards += '</div></div>'

    # Full self-contained HTML page inside an iframe srcdoc
    srcdoc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:Inter,sans-serif}}
body{{background:#f7f7f8;padding:12px;color:#111827}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
.qtxt{{font-size:.9rem;font-weight:600;margin-bottom:12px;line-height:1.5;color:#111827}}
.opts{{display:flex;flex-direction:column;gap:7px}}
.opt{{display:flex;align-items:center;gap:10px;padding:10px 13px;border-radius:7px;border:1.5px solid #e5e7eb;background:#f7f7f8;cursor:pointer;font-size:.84rem;color:#374151;transition:all .15s;user-select:none}}
.opt:hover{{border-color:#2563eb;background:#eff6ff;color:#2563eb}}
.opt.correct{{border-color:#16a34a!important;background:#f0fdf4!important;color:#15803d!important;pointer-events:none;font-weight:500}}
.opt.wrong{{border-color:#ef4444!important;background:#fef2f2!important;color:#dc2626!important;pointer-events:none}}
.opt.reveal{{border-color:#16a34a!important;background:#f0fdf4!important;color:#15803d!important;pointer-events:none;opacity:.7}}
.opt.locked{{pointer-events:none;opacity:.6}}
.ltr{{width:26px;height:26px;border-radius:50%;background:#f3f4f6;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;flex-shrink:0;color:#6b7280}}
.opt.correct .ltr{{background:#16a34a;color:#fff}}
.opt.wrong .ltr{{background:#ef4444;color:#fff}}
.opt.reveal .ltr{{background:#16a34a;color:#fff}}
.score{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;text-align:center;font-size:.88rem;color:#2563eb;font-weight:600;margin-top:8px;display:none}}
</style>
</head>
<body>
{cards}
<div class="score" id="sc"></div>
<script>
var D={questions_json};
var answered=new Array({total}).fill(false);
var score=0;
document.addEventListener('click',function(e){{
  var opt=e.target.closest('.opt');
  if(!opt)return;
  var qi=parseInt(opt.dataset.qi),oi=parseInt(opt.dataset.oi);
  if(answered[qi])return;
  answered[qi]=true;
  var q=D[qi],ci=q.correct;
  var all=document.querySelectorAll('[data-qi="'+qi+'"]');
  all.forEach(function(el){{el.classList.add('locked')}});
  if(oi===ci){{opt.classList.remove('locked');opt.classList.add('correct');score++;}}
  else{{
    opt.classList.remove('locked');opt.classList.add('wrong');
    var correct=document.querySelector('[data-qi="'+qi+'"][data-oi="'+ci+'"]');
    if(correct){{correct.classList.remove('locked');correct.classList.add('reveal');}}
  }}
  if(answered.every(Boolean)){{
    var sc=document.getElementById('sc');
    var erros={total}-score;
    var pct=Math.round(score/{total}*100);
    sc.style.display='block';
    sc.textContent=score+' certas  ·  '+erros+' erradas  ·  '+pct+'%';
  }}
}});
</script>
</body>
</html>"""

    # 260px per question (card + options + spacing) + 120px overhead
    height = total * 260 + 120
    return f'<iframe srcdoc="{srcdoc.replace(chr(34), "&quot;")}" style="width:100%;height:{height}px;border:none;border-radius:10px;display:block" scrolling="no"></iframe>'

def reset_db():
    engine.reset_collection()
    return build_docs_html()

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg:         #f7f7f8;
    --sidebar-bg: #ffffff;
    --surface:    #ffffff;
    --surface2:   #f0f2f5;
    --border:     #e5e7eb;
    --accent:     #2563eb;
    --accent-h:   #1d4ed8;
    --accent-soft:#eff6ff;
    --text:       #111827;
    --text-soft:  #374151;
    --muted:      #6b7280;
    --muted2:     #d1d5db;
    --danger:     #ef4444;
    --success:    #16a34a;
    --r:          10px;
    --r-sm:       7px;
    --shadow:     0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
}

body, .gradio-container, .gradio-container > div {
    background: var(--bg) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
}

footer, .gr-footer { display: none !important; }
.gradio-container { padding: 0 !important; max-width: 100% !important; overflow: hidden; }

/* Scroll fixes */
.panel { overflow-y: auto !important; }
.chat-col { overflow-y: hidden !important; }
.chatbot-wrap, .chat-col > div:first-child { flex: 1 !important; overflow-y: auto !important; }

/* Layout */
.app-layout {
    display: flex !important;
    height: 100vh !important;
    overflow: hidden !important;
    gap: 0 !important;
}

/* Sidebar */
.sidebar {
    width: 250px !important;
    min-width: 250px !important;
    max-width: 250px !important;
    background: var(--sidebar-bg) !important;
    border-right: 1px solid var(--border) !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    overflow: hidden !important;
}

.sb-header {
    padding: 20px 16px 14px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}
.sb-title { font-size: 0.92rem; font-weight: 600; color: var(--text); }
.sb-sub { font-size: 0.67rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; margin-top: 3px; }

.sb-section {
    padding: 14px 14px 6px;
    flex-shrink: 0;
}
.sb-label {
    font-size: 0.62rem;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
}

.docs-area {
    flex: 1;
    overflow-y: auto;
    padding: 0 8px;
}

.doc-list { padding: 2px 0; }
.doc-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 8px;
    border-radius: var(--r-sm);
    margin-bottom: 2px;
}
.doc-icon {
    font-size: 0.55rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    background: var(--accent);
    color: white;
    padding: 2px 5px;
    border-radius: 3px;
    flex-shrink: 0;
    letter-spacing: 0.05em;
}
.doc-name {
    font-size: 0.78rem;
    color: var(--text-soft);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.doc-count {
    font-size: 0.67rem;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    padding: 6px 8px 4px;
}
.empty-docs {
    font-size: 0.78rem;
    color: var(--muted);
    padding: 6px 8px;
    line-height: 1.6;
}

.sb-footer {
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    padding: 12px;
}

.upload-compact .wrap {
    border: 1.5px dashed var(--muted2) !important;
    border-radius: var(--r-sm) !important;
    background: transparent !important;
    min-height: 56px !important;
    transition: border-color 0.2s !important;
}
.upload-compact .wrap:hover { border-color: var(--accent) !important; }
.upload-compact span { font-size: 0.75rem !important; color: var(--muted) !important; }

/* Main */
.main-col {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    overflow: hidden !important;
    min-width: 0 !important;
}

/* Tabs */
.tab-wrap > div:first-child {
    background: var(--surface) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0 20px !important;
    box-shadow: var(--shadow) !important;
}
.tab-wrap button {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: var(--muted) !important;
    padding: 13px 14px !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    transition: color 0.15s !important;
}
.tab-wrap button:hover { color: var(--text) !important; }
.tab-wrap button.selected { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }

/* Chat */
.chat-col {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
}

.message.user .message-bubble-border {
    background: var(--accent) !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 11px 15px !important;
    border: none !important;
}
.message.user .message-bubble-border p,
.message.user .message-bubble-border span { color: #fff !important; }

.message.bot .message-bubble-border {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 11px 15px !important;
    box-shadow: var(--shadow) !important;
}
.message.bot .message-bubble-border p,
.message.bot .message-bubble-border span,
.message.bot .message-bubble-border li { color: var(--text) !important; }

.message-bubble-border p,
.message-bubble-border li,
.message-bubble-border span {
    font-size: 0.88rem !important;
    line-height: 1.75 !important;
    font-family: 'Inter', sans-serif !important;
}
.message-bubble-border strong { color: var(--accent) !important; font-weight: 600 !important; }

.chat-bar {
    flex-shrink: 0 !important;
    padding: 12px 20px 16px !important;
    background: var(--surface) !important;
    border-top: 1px solid var(--border) !important;
}
.chat-bar textarea {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    padding: 11px 15px !important;
    resize: none !important;
    box-shadow: var(--shadow) !important;
    transition: border-color 0.2s !important;
}
.chat-bar textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
    outline: none !important;
}
.chat-bar textarea::placeholder { color: var(--muted) !important; }

/* Panel */
.panel {
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 28px 32px 60px !important;
    max-width: 700px !important;
    margin: 0 auto !important;
    width: 100% !important;
}

/* Wrapper that actually scrolls */
.tab-wrap > div:last-child > div {
    overflow-y: auto !important;
    height: calc(100vh - 49px) !important;
}

/* Make panel content scrollable */
.panel {
    overflow-y: auto !important;
    max-height: calc(100vh - 49px) !important;
}
.panel-title { font-size: 1.1rem; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.panel-desc  { font-size: 0.82rem; color: var(--muted); margin-bottom: 20px; }

label > span {
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    color: var(--muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 5px !important;
    display: block !important;
}

.panel input[type=text], .panel textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-sm) !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    padding: 10px 13px !important;
    box-shadow: var(--shadow) !important;
    transition: border-color 0.2s !important;
}
.panel input[type=text]:focus, .panel textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
    outline: none !important;
}

/* Buttons */
button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    border-radius: var(--r-sm) !important;
    transition: all 0.15s !important;
    cursor: pointer !important;
}
.gr-button-primary, button.primary {
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    font-size: 0.85rem !important;
    padding: 10px 20px !important;
}
.gr-button-primary:hover, button.primary:hover {
    background: var(--accent-h) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
}
.gr-button-secondary, button.secondary {
    background: var(--surface) !important;
    color: var(--muted) !important;
    border: 1px solid var(--border) !important;
    font-size: 0.82rem !important;
    padding: 9px 14px !important;
    box-shadow: var(--shadow) !important;
}
.gr-button-secondary:hover, button.secondary:hover {
    color: var(--danger) !important;
    border-color: var(--danger) !important;
    background: #fef2f2 !important;
}

/* Output card */
.output-card {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    padding: 20px 22px !important;
    margin-top: 14px !important;
    min-height: 80px !important;
    box-shadow: var(--shadow) !important;
}

/* The panel itself scrolls - remove fixed height from output-card */
.tab-content-scroll {
    flex: 1 !important;
    overflow-y: auto !important;
    height: calc(100vh - 49px) !important;
}
.output-card p, .output-card li, .output-card span { color: var(--text) !important; font-size: 0.88rem !important; line-height: 1.8 !important; }
.output-card strong { color: var(--accent) !important; font-weight: 600 !important; }
.output-card h1, .output-card h2, .output-card h3 { color: var(--text) !important; font-weight: 600 !important; margin: 0.8em 0 0.3em !important; }
.output-card ul, .output-card ol { padding-left: 1.4em !important; color: var(--text) !important; }
.output-card hr { border-color: var(--border) !important; margin: 14px 0 !important; }

/* Slider */
input[type=range] { accent-color: var(--accent) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--muted2); border-radius: 99px; }

/* Quiz styles (injected via HTML) */
#quiz-area .quiz-wrap { display: flex; flex-direction: column; gap: 18px; margin-top: 4px; }
#quiz-area .q-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 18px 20px;
    box-shadow: var(--shadow);
}
#quiz-area .q-text { font-size: 0.9rem; font-weight: 600; color: var(--text); margin-bottom: 12px; line-height: 1.5; }
#quiz-area .q-options { display: flex; flex-direction: column; gap: 7px; }
#quiz-area .q-opt {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 13px;
    border-radius: var(--r-sm);
    border: 1.5px solid var(--border);
    background: var(--bg);
    cursor: pointer;
    font-size: 0.84rem;
    color: var(--text-soft);
    transition: border-color 0.15s, background 0.15s, color 0.15s;
    user-select: none;
}
#quiz-area .q-opt:hover { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
#quiz-area .q-opt.correct { border-color: #16a34a !important; background: #f0fdf4 !important; color: #15803d !important; font-weight: 500; pointer-events: none; }
#quiz-area .q-opt.wrong   { border-color: #ef4444 !important; background: #fef2f2 !important; color: #dc2626 !important; pointer-events: none; }
#quiz-area .q-opt.reveal  { border-color: #16a34a !important; background: #f0fdf4 !important; color: #15803d !important; pointer-events: none; opacity: 0.7; }
#quiz-area .q-opt.locked  { pointer-events: none; opacity: 0.6; }
#quiz-area .q-letter {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: #f3f4f6;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700;
    flex-shrink: 0; color: var(--muted);
    transition: background 0.15s, color 0.15s;
}
#quiz-area .q-opt.correct .q-letter { background: #16a34a; color: white; }
#quiz-area .q-opt.wrong   .q-letter { background: #ef4444; color: white; }
#quiz-area .q-opt.reveal  .q-letter { background: #16a34a; color: white; }
#quiz-area .q-fb {
    margin-top: 10px;
    padding: 10px 14px;
    border-radius: var(--r-sm);
    font-size: 0.8rem;
    line-height: 1.6;
    display: none;
}
#quiz-area .q-fb.show { display: block; }
#quiz-area .q-fb.ok  { background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }
#quiz-area .q-fb.err { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
#quiz-area .quiz-score {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: var(--r);
    padding: 16px 20px;
    text-align: center;
    font-size: 0.88rem;
    color: var(--accent);
    font-weight: 600;
    margin-top: 8px;
    display: none;
}
#quiz-area .quiz-loading {
    color: var(--muted);
    font-size: 0.85rem;
    padding: 20px 0;
    text-align: center;
}
#quiz-area .quiz-error {
    color: var(--danger);
    font-size: 0.82rem;
    padding: 14px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--r-sm);
}
"""

# ── Quiz JS ───────────────────────────────────────────────────────────────────

QUIZ_JS = """
// Event delegation - catches clicks on q-opt elements anywhere on the page
document.addEventListener('click', function(e) {
    const opt = e.target.closest('.q-opt');
    if (!opt) return;
    const qi = parseInt(opt.getAttribute('data-qi'));
    const oi = parseInt(opt.getAttribute('data-oi'));
    if (isNaN(qi) || isNaN(oi)) return;
    pickAnswer(qi, oi);
});

function getQuizData() {
    const wrap = document.getElementById('quiz-wrap');
    if (!wrap) return null;
    const b64 = wrap.getAttribute('data-questions');
    if (!b64) return null;
    // Reset state if new quiz loaded (different data)
    if (window.__quizB64 !== b64) {
        window.__quizB64 = b64;
        try {
            window.__quizData = JSON.parse(atob(b64));
            window.__quizAnswered = new Array(window.__quizData.length).fill(false);
            window.__quizScore = 0;
        } catch(e) { return null; }
    }
    return window.__quizData;
}

function pickAnswer(qi, oi) {
    const data = getQuizData();
    if (!data) return;
    if (window.__quizAnswered[qi]) return;
    window.__quizAnswered[qi] = true;

    const q = data[qi];
    const correctIdx = typeof q.correct === 'number' ? q.correct : 0;
    const letters = ['A','B','C','D','E'];

    // Lock all options and highlight correct
    for (let i = 0; i < q.options.length; i++) {
        const el = document.getElementById('o-' + qi + '-' + i);
        if (!el) continue;
        el.style.pointerEvents = 'none';
        if (i === correctIdx && i !== oi) el.classList.add('reveal');
    }

    const chosen = document.getElementById('o-' + qi + '-' + oi);
    if (oi === correctIdx) {
        chosen.classList.add('correct');
        window.__quizScore = (window.__quizScore || 0) + 1;
    } else {
        chosen.classList.add('wrong');
    }

    // Show score when all answered
    if (window.__quizAnswered.every(Boolean)) {
        const sc = document.getElementById('qscore');
        if (sc) {
            const total = data.length;
            const erros = total - window.__quizScore;
            const pct = Math.round((window.__quizScore / total) * 100);
            sc.style.display = 'block';
            sc.innerHTML = window.__quizScore + ' certas &nbsp;&middot;&nbsp; ' + erros + ' erradas &nbsp;&middot;&nbsp; ' + pct + '%';
        }
    }
}
"""

# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="uRobot Tutor") as demo:

    gr.HTML(f"<script>{QUIZ_JS}</script>")

    with gr.Row(elem_classes=["app-layout"]):

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        with gr.Column(elem_classes=["sidebar"], scale=0, min_width=250):

            gr.HTML("""
            <div class="sb-header">
                <div class="sb-title">uRobot Tutor</div>
                <div class="sb-sub">local · privado · sem internet</div>
            </div>
            """)

            gr.HTML('<div class="sb-section"><div class="sb-label">Documentos</div></div>')

            docs_html = gr.HTML(
                value=build_docs_html(),
                elem_classes=["docs-area"],
            )

            gr.HTML('<div class="sb-footer">')
            file_input = gr.File(
                label="",
                file_types=[".pdf", ".txt", ".md"],
                file_count="multiple",
                elem_classes=["upload-compact"],
                show_label=False,
            )
            with gr.Row():
                upload_btn = gr.Button("Carregar", variant="primary", size="sm")
                reset_btn  = gr.Button("Limpar tudo", variant="secondary", size="sm")
            gr.HTML('</div>')

        # ── MAIN ─────────────────────────────────────────────────────────────
        with gr.Column(elem_classes=["main-col"], scale=1):

            with gr.Tabs(elem_classes=["tab-wrap"]):

                # Chat
                with gr.Tab("Chat"):
                    with gr.Column(elem_classes=["chat-col"]):
                        chatbot = gr.Chatbot(
                            label="",
                            height=540,
                            show_label=False,
                            placeholder=(
                                "<div style='display:flex;flex-direction:column;"
                                "align-items:center;justify-content:center;"
                                "height:100%;gap:10px;color:#9ca3af;padding:40px'>"
                                "<svg width='32' height='32' viewBox='0 0 24 24' fill='none' "
                                "stroke='#d1d5db' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'>"
                                "<path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/>"
                                "</svg>"
                                "<span style='font-size:0.84rem'>Carrega os teus materiais e coloca as tuas questoes</span>"
                                "</div>"
                            ),
                        )
                        with gr.Row(elem_classes=["chat-bar"]):
                            chat_input = gr.Textbox(
                                placeholder="Escreve a tua pergunta...",
                                show_label=False,
                                lines=1,
                                max_lines=5,
                                scale=7,
                            )
                            send_btn  = gr.Button("Enviar",  variant="primary",   scale=1, min_width=80)
                            clear_btn = gr.Button("Limpar", variant="secondary", scale=1, min_width=80)

                # Resumos
                with gr.Tab("Resumos"):
                    with gr.Column(elem_classes=["panel"]):
                        gr.HTML("""
                        <div class="panel-title">Resumo automatico</div>
                        <div class="panel-desc">Gera um resumo estruturado a partir dos teus materiais.</div>
                        """)
                        summary_topic = gr.Textbox(
                            label="Topico",
                            placeholder="ex: fotossintese, redes neuronais, Segunda Guerra Mundial",
                            lines=1,
                        )
                        summary_btn = gr.Button("Gerar Resumo", variant="primary")
                        summary_output = gr.Markdown(value="", elem_classes=["output-card"])

                # Questionarios
                with gr.Tab("Questionarios"):
                    with gr.Column(elem_classes=["panel"]):
                        gr.HTML("""
                        <div class="panel-title">Questionario interativo</div>
                        <div class="panel-desc">Seleciona a resposta e recebe feedback imediato com a explicacao.</div>
                        """)
                        quiz_topic = gr.Textbox(
                            label="Topico",
                            placeholder="ex: osmose, Revolucao Francesa, algoritmos de ordenacao",
                            lines=1,
                        )
                        n_questions = gr.Slider(
                            minimum=3, maximum=10, value=5, step=1,
                            label="Numero de perguntas",
                        )
                        quiz_btn = gr.Button("Gerar Questionario", variant="primary")
                        quiz_output_html = gr.HTML(
                            value='<div style="color:#6b7280;font-size:0.84rem;text-align:center;padding:20px 0">Escreve um topico e clica em Gerar Questionario.</div>',
                            elem_id="quiz-area"
                        )

    # ── Events ────────────────────────────────────────────────────────────────
    upload_btn.click(upload_files, inputs=[file_input], outputs=[docs_html])
    reset_btn.click(reset_db, outputs=[docs_html])

    send_btn.click(chat_send, inputs=[chat_input, chatbot], outputs=[chatbot, chat_input])
    chat_input.submit(chat_send, inputs=[chat_input, chatbot], outputs=[chatbot, chat_input])
    clear_btn.click(clear_chat, outputs=[chatbot, chat_input])

    summary_btn.click(make_summary, inputs=[summary_topic], outputs=[summary_output])

    quiz_btn.click(
        make_quiz,
        inputs=[quiz_topic, n_questions],
        outputs=[quiz_output_html],
    )

if __name__ == "__main__":
    print("A iniciar uRobot Tutor...")
    print("Acede em: http://localhost:7860")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, css=CSS)