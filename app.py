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
    return f'<div class="doc-list">{items}<div class="doc-count">{len(info["files"])} documento{"s" if len(info["files"]) != 1 else ""} carregado{"s" if len(info["files"]) != 1 else ""}</div></div>'

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
        return '<p style="color:#64748b;font-size:0.84rem">Escreve um topico para gerar o questionario.</p>'
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

    cards = ""
    for qi, q in enumerate(questions):
        opts = q.get("options", [])
        cards += f'<div class="card"><div class="qtxt">{qi+1}. {q.get("question","")}</div><div class="opts">'
        for oi, opt in enumerate(opts):
            letter = letters[oi] if oi < len(letters) else str(oi)
            cards += f'<div class="opt" data-qi="{qi}" data-oi="{oi}"><div class="ltr">{letter}</div><span>{opt}</span></div>'
        cards += '</div></div>'

    srcdoc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:Inter,sans-serif}}
body{{background:#f8fafc;padding:12px;color:#0f172a}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin-bottom:16px;box-shadow:0 4px 6px -1px rgb(0 0 0 / .05)}}
.qtxt{{font-size:.9rem;font-weight:600;margin-bottom:12px;line-height:1.5;color:#0f172a}}
.opts{{display:flex;flex-direction:column;gap:7px}}
.opt{{display:flex;align-items:center;gap:10px;padding:10px 13px;border-radius:8px;border:1.5px solid #e2e8f0;background:#f8fafc;cursor:pointer;font-size:.84rem;color:#334155;transition:all .15s;user-select:none}}
.opt:hover{{border-color:#6366f1;background:#e0e7ff;color:#6366f1}}
.opt.correct{{border-color:#10b981!important;background:#d1fae5!important;color:#047857!important;pointer-events:none;font-weight:500}}
.opt.wrong{{border-color:#ef4444!important;background:#fee2e2!important;color:#b91c1c!important;pointer-events:none}}
.opt.reveal{{border-color:#10b981!important;background:#d1fae5!important;color:#047857!important;pointer-events:none;opacity:.7}}
.opt.locked{{pointer-events:none;opacity:.6}}
.ltr{{width:26px;height:26px;border-radius:50%;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;flex-shrink:0;color:#64748b}}
.opt.correct .ltr{{background:#10b981;color:#fff}}
.opt.wrong .ltr{{background:#ef4444;color:#fff}}
.opt.reveal .ltr{{background:#10b981;color:#fff}}
.score{{background:#e0e7ff;border:1px solid #c7d2fe;border-radius:12px;padding:14px 18px;text-align:center;font-size:.88rem;color:#6366f1;font-weight:600;margin-top:8px;display:none}}
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

    height = total * 260 + 120
    return f'<iframe srcdoc="{srcdoc.replace(chr(34), "&quot;")}" style="width:100%;height:{height}px;border:none;border-radius:10px;display:block" scrolling="no"></iframe>'

def make_flashcards(topic, n):
    import json as _json
    if not topic.strip():
        return '<p style="color:#64748b;font-size:0.84rem">Escreve um topico para gerar os flashcards.</p>'
    raw = engine.generate_flashcards(topic, int(n))
    raw = raw.strip().replace("```json","").replace("```","").strip()
    start = raw.find("["); end = raw.rfind("]")
    if start == -1 or end == -1:
        return '<p style="color:#ef4444;font-size:0.84rem">Nao foi possivel gerar flashcards. Tenta novamente.</p>'
    raw = raw[start:end+1]
    if raw == "[]":
        return '<p style="color:#ef4444;font-size:0.84rem">Nao encontrei informacao suficiente nos materiais.</p>'
    try:
        cards = _json.loads(raw)
    except Exception:
        return '<p style="color:#ef4444;font-size:0.84rem">Erro ao processar os flashcards. Tenta novamente.</p>'

    total = len(cards)
    cards_json = _json.dumps(cards, ensure_ascii=False)

    cards_html = ""
    for i, c in enumerate(cards):
        front = c.get("front", "")
        back = c.get("back", "")
        cards_html += f"""<div class="fc" id="fc{i}">
  <div class="fc-inner" id="fci{i}">
    <div class="fc-front"><div class="fc-num">{i+1} / {total}</div><div class="fc-txt">{front}</div><div class="fc-hint">clica para ver a resposta</div></div>
    <div class="fc-back"><div class="fc-num">{i+1} / {total}</div><div class="fc-txt">{back}</div><div class="fc-hint">clica para virar</div></div>
  </div>
</div>"""

    srcdoc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:Inter,sans-serif}}
body{{background:#f8fafc;padding:16px;color:#0f172a}}
h3{{font-size:.8rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px}}
.nav{{display:flex;gap:10px;margin-bottom:16px;align-items:center}}
.nav button{{padding:8px 18px;border-radius:8px;border:1.5px solid #e2e8f0;background:#fff;font-size:.82rem;font-weight:500;cursor:pointer;color:#334155;transition:all .15s}}
.nav button:hover{{border-color:#6366f1;color:#6366f1;background:#e0e7ff}}
.nav .prog{{flex:1;text-align:center;font-size:.8rem;color:#64748b}}
.fc{{display:none;perspective:1000px;height:200px;cursor:pointer}}
.fc.active{{display:block}}
.fc-inner{{width:100%;height:100%;position:relative;transform-style:preserve-3d;transition:transform .5s ease}}
.fc.flipped .fc-inner{{transform:rotateY(180deg)}}
.fc-front,.fc-back{{position:absolute;width:100%;height:100%;backface-visibility:hidden;-webkit-backface-visibility:hidden;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;text-align:center;box-shadow:0 4px 6px -1px rgb(0 0 0 / .05)}}
.fc-front{{background:#fff;border:1.5px solid #e2e8f0}}
.fc-back{{background:#6366f1;border:1.5px solid #6366f1;transform:rotateY(180deg)}}
.fc-num{{font-size:.7rem;color:#94a3b8;margin-bottom:10px;font-weight:500}}
.fc-back .fc-num{{color:rgba(255,255,255,.7)}}
.fc-txt{{font-size:1rem;font-weight:600;line-height:1.5;color:#0f172a}}
.fc-back .fc-txt{{color:#fff}}
.fc-hint{{font-size:.72rem;color:#94a3b8;margin-top:12px}}
.fc-back .fc-hint{{color:rgba(255,255,255,.6)}}
.dots{{display:flex;justify-content:center;gap:6px;margin-top:14px;flex-wrap:wrap}}
.dot{{width:8px;height:8px;border-radius:50%;background:#e2e8f0;cursor:pointer;transition:background .2s}}
.dot.active{{background:#6366f1}}
.dot.seen{{background:#a5b4fc}}
</style>
</head>
<body>
<h3>Flashcards — {total} cartoes</h3>
<div class="nav">
  <button onclick="move(-1)">&#8592; Anterior</button>
  <div class="prog" id="prog">1 / {total}</div>
  <button onclick="move(1)">Seguinte &#8594;</button>
</div>
{cards_html}
<div class="dots" id="dots"></div>
<script>
var cur=0,total={total},seen=new Array(total).fill(false);
seen[0]=true;
function show(i){{
  document.querySelectorAll('.fc').forEach(function(el){{el.classList.remove('active','flipped')}});
  var el=document.getElementById('fc'+i);
  if(el){{el.classList.add('active');}}
  document.getElementById('prog').textContent=(i+1)+' / '+total;
  updateDots();
}}
function move(d){{
  cur=Math.max(0,Math.min(total-1,cur+d));
  seen[cur]=true;
  show(cur);
}}
document.addEventListener('click',function(e){{
  var fc=e.target.closest('.fc');
  if(fc){{fc.classList.toggle('flipped');return;}}
  var dot=e.target.closest('.dot');
  if(dot){{cur=parseInt(dot.dataset.i);seen[cur]=true;show(cur);}}
}});
function updateDots(){{
  var c=document.getElementById('dots');
  c.innerHTML='';
  for(var i=0;i<total;i++){{
    var d=document.createElement('div');
    d.className='dot'+(i===cur?' active':seen[i]?' seen':'');
    d.dataset.i=i;d.title='Cartao '+(i+1);
    c.appendChild(d);
  }}
}}
show(0);
</script>
</body>
</html>"""

    height = 380
    return f'<iframe srcdoc="{srcdoc.replace(chr(34), "&quot;")}" style="width:100%;height:{height}px;border:none;border-radius:10px;display:block" scrolling="no"></iframe>'

def make_bullets(topic):
    if not topic.strip():
        return "Escreve um topico para gerar o resumo."
    return engine.bullets_summary(topic)

def make_fill(topic, n):
    import json as _json
    if not topic.strip():
        return '<p style="color:#64748b;font-size:0.84rem">Escreve um topico.</p>'
    raw = engine.generate_fill(topic, int(n))
    raw = raw.strip().replace("```json","").replace("```","").strip()
    s = raw.find("["); e = raw.rfind("]")
    if s == -1 or e == -1 or raw[s:e+1] == "[]":
        return '<p style="color:#ef4444;font-size:0.84rem">Nao foi possivel gerar exercicios. Tenta novamente.</p>'
    try:
        exercises = _json.loads(raw[s:e+1])
    except Exception:
        return '<p style="color:#ef4444;font-size:0.84rem">Erro ao processar. Tenta novamente.</p>'

    total = len(exercises)
    ex_json = _json.dumps(exercises, ensure_ascii=False)

    ex_html = ""
    for i, ex in enumerate(exercises):
        display = ex.get("display") or ex.get("sentence","")
        ex_html += f'''<div class="ex" id="ex{i}">
  <div class="ex-num">Exercicio {i+1}</div>
  <div class="ex-sent">{display}</div>
  <div class="ex-row">
    <input class="ex-input" id="inp{i}" placeholder="Escreve a palavra em falta..." autocomplete="off">
    <button class="ex-btn" onclick="checkFill({i})">Verificar</button>
  </div>
  <div class="ex-fb" id="fb{i}"></div>
</div>'''

    srcdoc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:Inter,sans-serif}}
body{{background:#f8fafc;padding:14px;color:#0f172a}}
.ex{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin-bottom:14px;box-shadow:0 4px 6px -1px rgb(0 0 0 / .05)}}
.ex-num{{font-size:.7rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px}}
.ex-sent{{font-size:.92rem;line-height:1.6;color:#0f172a;margin-bottom:12px;font-weight:500}}
.ex-row{{display:flex;gap:8px}}
.ex-input{{flex:1;padding:9px 13px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.86rem;color:#0f172a;outline:none;transition:border-color .15s}}
.ex-input:focus{{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.1)}}
.ex-input.ok{{border-color:#10b981;background:#d1fae5}}
.ex-input.err{{border-color:#ef4444;background:#fee2e2}}
.ex-btn{{padding:9px 18px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-size:.84rem;font-weight:500;cursor:pointer;white-space:nowrap;transition:background .15s}}
.ex-btn:hover{{background:#4f46e5}}
.ex-fb{{margin-top:10px;font-size:.8rem;padding:8px 12px;border-radius:6px;display:none}}
.ex-fb.ok{{display:block;background:#d1fae5;border:1px solid #a7f3d0;color:#047857}}
.ex-fb.err{{display:block;background:#fee2e2;border:1px solid #fecaca;color:#b91c1c}}
.score{{background:#e0e7ff;border:1px solid #c7d2fe;border-radius:12px;padding:14px;text-align:center;font-size:.88rem;color:#6366f1;font-weight:600;margin-top:4px;display:none}}
</style></head><body>
{ex_html}
<div class="score" id="sc"></div>
<script>
var D={ex_json};
var answered=new Array({total}).fill(false);
var score=0;
function checkFill(i){{
  if(answered[i])return;
  answered[i]=true;
  var inp=document.getElementById('inp'+i);
  var fb=document.getElementById('fb'+i);
  var ans=D[i].answer.trim().toLowerCase();
  var val=inp.value.trim().toLowerCase();
  if(val===ans||ans.includes(val)&&val.length>2){{
    inp.className='ex-input ok';
    fb.className='ex-fb ok';
    fb.textContent='Correto! A resposta e: '+D[i].answer;
    score++;
  }}else{{
    inp.className='ex-input err';
    fb.className='ex-fb err';
    fb.textContent='Errado. A resposta correta e: '+D[i].answer;
  }}
  inp.disabled=true;
  if(answered.every(Boolean)){{
    var sc=document.getElementById('sc');
    var pct=Math.round(score/{total}*100);
    sc.style.display='block';
    sc.textContent=score+' certas  ·  '+({total}-score)+' erradas  ·  '+pct+'%';
  }}
}}
document.addEventListener('keydown',function(e){{
  if(e.key==='Enter'){{
    var inp=e.target;
    if(!inp.classList.contains('ex-input'))return;
    var i=parseInt(inp.id.replace('inp',''));
    checkFill(i);
  }}
}});
</script>
</body></html>"""

    height = total * 155 + 80
    return f'<iframe srcdoc="{srcdoc.replace(chr(34), "&quot;")}" style="width:100%;height:{height}px;border:none;border-radius:10px;display:block" scrolling="no"></iframe>'

def make_compare(topic_a, topic_b):
    import json as _json
    if not topic_a.strip() or not topic_b.strip():
        return '<p style="color:#64748b;font-size:0.84rem">Escreve os dois topicos para comparar.</p>'
    raw = engine.generate_compare(topic_a, topic_b)
    raw = raw.strip().replace("```json","").replace("```","").strip()
    s = raw.find("["); e = raw.rfind("]")
    if s == -1 or e == -1 or raw[s:e+1] == "[]":
        return '<p style="color:#ef4444;font-size:0.84rem">Nao foi possivel gerar a comparacao. Tenta novamente.</p>'
    try:
        rows = _json.loads(raw[s:e+1])
    except Exception:
        return '<p style="color:#ef4444;font-size:0.84rem">Erro ao processar. Tenta novamente.</p>'

    table = f'''<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:.86rem">
<thead><tr>
  <th style="background:#f1f5f9;padding:11px 14px;text-align:left;border:1px solid #e2e8f0;color:#64748b;font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;width:24%">Categoria</th>
  <th style="background:#e0e7ff;padding:11px 14px;text-align:left;border:1px solid #e2e8f0;color:#6366f1;font-weight:600">{topic_a}</th>
  <th style="background:#d1fae5;padding:11px 14px;text-align:left;border:1px solid #e2e8f0;color:#10b981;font-weight:600">{topic_b}</th>
</tr></thead><tbody>'''

    for i, row in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
        table += f'''<tr style="background:{bg}">
  <td style="padding:10px 14px;border:1px solid #e2e8f0;font-weight:600;color:#334155">{row.get("category","")}</td>
  <td style="padding:10px 14px;border:1px solid #e2e8f0;color:#0f172a;line-height:1.5">{row.get("a","")}</td>
  <td style="padding:10px 14px;border:1px solid #e2e8f0;color:#0f172a;line-height:1.5">{row.get("b","")}</td>
</tr>'''

    table += "</tbody></table></div>"
    return table

def reset_db():
    engine.reset_collection()
    return build_docs_html()

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

with gr.Blocks(title="Document Helper") as demo:

    gr.HTML(f"<script>{QUIZ_JS}</script>")

    with gr.Row(elem_classes=["app-layout"]):

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        with gr.Column(elem_classes=["sidebar"], scale=0, min_width=250):

            gr.HTML("""
            <div class="sb-header">
                <div class="logo-wrap">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    <div class="logo-text">
                        <span class="logo-main">Document Helper</span>
                    </div>
                </div>
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
                                "height:100%;gap:10px;color:#94a3b8;padding:40px'>"
                                "<svg width='32' height='32' viewBox='0 0 24 24' fill='none' "
                                "stroke='#cbd5e1' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'>"
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

                # Flashcards
                with gr.Tab("Flashcards"):
                    with gr.Column(elem_classes=["panel"]):
                        gr.HTML("""
                        <div class="panel-title">Flashcards</div>
                        <div class="panel-desc">Cartoes de estudo interativos — clica para ver a resposta.</div>
                        """)
                        flash_topic = gr.Textbox(
                            label="Topico",
                            placeholder="ex: redes neuronais, fotossintese, algoritmos",
                            lines=1,
                        )
                        n_flashcards = gr.Slider(
                            minimum=4, maximum=20, value=8, step=1,
                            label="Numero de flashcards",
                        )
                        flash_btn = gr.Button("Gerar Flashcards", variant="primary")
                        flash_output = gr.HTML(
                            value='<div style="color:#64748b;font-size:0.84rem;text-align:center;padding:20px 0">Escreve um topico e clica em Gerar Flashcards.</div>'
                        )

                # Completar Frases
                with gr.Tab("Completar Frases"):
                    with gr.Column(elem_classes=["panel"]):
                        gr.HTML("""
                        <div class="panel-title">Exercicios de completar</div>
                        <div class="panel-desc">Frases retiradas dos materiais com uma palavra em falta — escreve e verifica.</div>
                        """)
                        fill_topic = gr.Textbox(
                            label="Topico",
                            placeholder="ex: LLMs, osmose, Segunda Guerra Mundial",
                            lines=1,
                        )
                        n_fill = gr.Slider(minimum=3, maximum=10, value=5, step=1, label="Numero de exercicios")
                        fill_btn = gr.Button("Gerar Exercicios", variant="primary")
                        fill_output = gr.HTML(
                            value='<div style="color:#64748b;font-size:0.84rem;text-align:center;padding:20px 0">Escreve um topico e clica em Gerar Exercicios.</div>'
                        )

                # Comparar Conceitos
                with gr.Tab("Comparar"):
                    with gr.Column(elem_classes=["panel"]):
                        gr.HTML("""
                        <div class="panel-title">Comparacao de conceitos</div>
                        <div class="panel-desc">Tabela lado a lado com semelhancas e diferencas entre dois topicos.</div>
                        """)
                        compare_a = gr.Textbox(label="Topico A", placeholder="ex: redes neuronais", lines=1)
                        compare_b = gr.Textbox(label="Topico B", placeholder="ex: algoritmos geneticos", lines=1)
                        compare_btn = gr.Button("Comparar", variant="primary")
                        compare_output = gr.HTML(
                            value='<div style="color:#64748b;font-size:0.84rem;text-align:center;padding:20px 0">Escreve os dois topicos e clica em Comparar.</div>'
                        )

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
                            value='<div style="color:#64748b;font-size:0.84rem;text-align:center;padding:20px 0">Escreve um topico e clica em Gerar Questionario.</div>',
                            elem_id="quiz-area"
                        )

    # ── Events ────────────────────────────────────────────────────────────────
    upload_btn.click(upload_files, inputs=[file_input], outputs=[docs_html])
    reset_btn.click(reset_db, outputs=[docs_html])

    send_btn.click(chat_send, inputs=[chat_input, chatbot], outputs=[chatbot, chat_input])
    chat_input.submit(chat_send, inputs=[chat_input, chatbot], outputs=[chatbot, chat_input])
    clear_btn.click(clear_chat, outputs=[chatbot, chat_input])

    summary_btn.click(make_summary, inputs=[summary_topic], outputs=[summary_output])
    flash_btn.click(make_flashcards, inputs=[flash_topic, n_flashcards], outputs=[flash_output])
    fill_btn.click(make_fill, inputs=[fill_topic, n_fill], outputs=[fill_output])
    compare_btn.click(make_compare, inputs=[compare_a, compare_b], outputs=[compare_output])

    quiz_btn.click(
        make_quiz,
        inputs=[quiz_topic, n_questions],
        outputs=[quiz_output_html],
    )

if __name__ == "__main__":
    print("A iniciar Document Helper...")
    print("Acede em: http://localhost:7860")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, css="style.css", theme=gr.themes.Base())