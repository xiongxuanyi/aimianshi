/* =========================================================
 * AI 模拟面试前端控制器（原生 JS · 无构建）
 * 功能：
 *   0. 用户身份（注册/匿名，写入 users 表；接口未就绪时 localStorage 兜底）
 *   1. Setup：拖拽上传简历 / 粘贴 JD / 生成题库
 *   2. Interview：文字/语音作答、SSE 流式渲染、浏览器 TTS 朗读
 *   3. History：MySQL 历史会话列表（接口未就绪时友好提示，不报错）
 *   4. Result：多维度分数 + 评语 + 建议渲染
 * 要点：
 *   - SSE 采用 fetch + ReadableStream 逐行读取，严格按 data: 前缀解析
 *   - 语音 API：SpeechRecognition（webkit 前缀）+ speechSynthesis
 *   - 所有后端新接口（users/history）做 404 容错，后端未实现也不影响主流程
 * ========================================================= */
(function () {
  'use strict';

  // ========== 全局状态 ==========
  const state = {
    user: null,           // {id, nickname, unique_key}
    resume: null,
    resumeFile: null,
    jd: null,
    jdText: '',
    questions: [],
    questionsRaw: [],
    sessionId: null,
    position: '',
    welcome: '',
    totalRounds: 0,
    round: 0,
    autoTTS: true,
    interviewing: false,
  };

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  // ========== 通用工具 ==========
  function toast(msg, type = 'info', timeout = 3200) {
    const wrap = $('#toastHost');
    if (!wrap) return;
    const el = document.createElement('div');
    const bg = {
      success: 'bg-emerald-50 border-emerald-200 text-emerald-700',
      error:   'bg-red-50 border-red-200 text-red-700',
      info:    'bg-sky-50 border-sky-200 text-sky-700',
      warn:    'bg-amber-50 border-amber-200 text-amber-700',
    }[type] || 'bg-sky-50 border-sky-200 text-sky-700';
    const icon = { success: '✅', error: '❌', info: 'ℹ️', warn: '⚠️' }[type] || 'ℹ️';
    el.className = `px-3 py-2.5 rounded-xl border ${bg} shadow-soft text-sm animate-fadeInUp`;
    el.innerHTML = `<div class="flex items-start gap-2"><span>${icon}</span><div class="flex-1 whitespace-pre-wrap break-words">${escapeHtml(msg)}</div></div>`;
    wrap.appendChild(el);
    setTimeout(() => {
      el.style.transform = 'translateY(-8px)';
      el.style.opacity = '0';
      el.style.transition = 'all .25s';
      setTimeout(() => el.remove(), 280);
    }, timeout);
  }

  function escapeHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function showModalErr(title, body) {
    const d = $('#errModal');
    $('#errTitle').textContent = title;
    $('#errBody').textContent = body;
    if (d && typeof d.showModal === 'function') d.showModal();
    else alert(`${title}\n${body}`);
  }

  function switchTab(name) {
    $$('.tab-pane').forEach((p) => p.classList.add('hidden'));
    const view = $(`#${name}View`);
    if (view) view.classList.remove('hidden');
    $$('.nav-btn').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (name === 'history') loadHistory();
  }

  // ========== 视图 0：用户身份 ==========
  function initUser() {
    // 本地缓存恢复
    try {
      const cached = JSON.parse(localStorage.getItem('ai_interview_user') || 'null');
      if (cached) {
        state.user = cached;
        renderUserTag();
      }
    } catch (_) {}

    const btn = $('#userEnsureBtn');
    if (btn) btn.addEventListener('click', ensureUser);
  }

  function renderUserTag() {
    const tag = $('#userTag');
    if (!tag) return;
    if (state.user && state.user.id) {
      tag.textContent = `当前：${state.user.nickname || '候选人'}（uid=${state.user.id}，结果将持久化）`;
      tag.className = 'text-xs text-emerald-600 font-medium';
    } else {
      tag.textContent = '当前：未登录 / 匿名模式（本地临时）';
      tag.className = 'text-xs text-slate-500';
    }
  }

  async function ensureUser() {
    const nickname = ($('#userNick')?.value || '面试候选人').trim();
    const email = ($('#userEmail')?.value || '').trim();
    const pwd = $('#userPwd')?.value || '';

    // 优先调后端 /api/users（MySQL 持久化）；接口未就绪则 localStorage 匿名兜底
    try {
      const resp = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname, email, password: pwd || null }),
      });
      if (resp.ok) {
        const data = await resp.json();
        state.user = { id: data.id || data.user_id, nickname: data.nickname || nickname, unique_key: data.unique_key };
        localStorage.setItem('ai_interview_user', JSON.stringify(state.user));
        renderUserTag();
        toast('身份已确认并写入数据库 ✅', 'success');
        return;
      }
      // 404/501 等：后端尚未提供该接口，走匿名兜底
      throw new Error('users api not ready');
    } catch (_) {
      // 匿名本地兜底
      const anonId = 'anon_' + Math.random().toString(36).slice(2, 10);
      state.user = { id: anonId, nickname, unique_key: anonId };
      localStorage.setItem('ai_interview_user', JSON.stringify(state.user));
      renderUserTag();
      toast('已使用本地匿名身份（后端用户接口待接入 MySQL 后自动持久化）', 'warn', 4200);
    }
  }

  // ========== 视图 1：Setup ==========
  function initSetup() {
    const dz = $('#resumeDropzone');
    const input = $('#resumeInput');
    if (dz && input) {
      dz.addEventListener('click', () => input.click());
      dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
      dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
      dz.addEventListener('drop', (e) => {
        e.preventDefault(); dz.classList.remove('dragover');
        const f = e.dataTransfer.files && e.dataTransfer.files[0];
        if (f) uploadResume(f);
      });
      input.addEventListener('change', (e) => {
        const f = e.target.files && e.target.files[0];
        if (f) uploadResume(f);
      });
    }
    const clearBtn = $('#clearResume');
    if (clearBtn) clearBtn.addEventListener('click', () => {
      state.resume = null;
      $('#resumeParsedCard').classList.add('hidden');
      if (input) input.value = '';
    });

    const jdEl = $('#jdText');
    if (jdEl) jdEl.addEventListener('input', () => {
      state.jdText = jdEl.value;
      const cc = $('#jdCharCount');
      if (cc) cc.textContent = state.jdText.length;
    });

    const demoBtn = $('#fillDemoBtn');
    if (demoBtn) demoBtn.addEventListener('click', () => {
      jdEl.value =
`岗位名称：中级 Python 后端开发工程师

岗位职责：
1. 负责公司核心 SaaS 产品后端开发，围绕用户体系、订单、支付等核心模块进行设计与迭代；
2. 与前端、产品、数据团队协作，保障接口稳定，支持并发量 10w+ 场景；
3. 参与代码评审、技术方案讨论，推动系统性能与质量持续优化。

任职要求：
1. 3 年以上 Python 后端经验，熟练使用 FastAPI / Django / Flask 任一主流框架；
2. 熟悉 MySQL / PostgreSQL，有 SQL 调优与索引优化经验；
3. 熟悉 Redis、Kafka、Celery 等中间件，能胜任异步任务与缓存设计；
4. 具备高并发、分布式项目经验优先；
5. 具备良好沟通表达与团队协作能力，自驱力强。`;
      jdEl.dispatchEvent(new Event('input'));
      toast('已填入演示 JD，可直接点击右侧按钮生成题库', 'info');
    });

    const genBtn = $('#generateBtn');
    if (genBtn) genBtn.addEventListener('click', onGenerateStart);
  }

  function uploadResume(file) {
    state.resumeFile = file;
    const nameEl = $('#resumeFileName');
    if (nameEl) nameEl.textContent = `${file.name}（${(file.size/1024).toFixed(1)} KB）`;
    const wrap = $('#resumeProgressWrap');
    const bar = $('#resumeProgressBar');
    const lbl = $('#resumeProgressLabel');
    if (wrap) wrap.classList.remove('hidden');
    if (bar) bar.style.width = '0%';
    if (lbl) lbl.textContent = '上传中 0%';

    const fd = new FormData();
    fd.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/resume/parse', true);
    xhr.upload.onprogress = (ev) => {
      const p = ev.lengthComputable ? Math.round((ev.loaded / ev.total) * 100) : 10;
      if (bar) bar.style.width = p + '%';
      if (lbl) lbl.textContent = '上传解析中… ' + p + '%';
    };
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText || '{}');
        if (xhr.status !== 200 || data.ok === false) {
          toast('简历解析失败：' + (data.error || xhr.statusText), 'error', 4500);
          if (wrap) wrap.classList.add('hidden');
          return;
        }
        state.resume = data;
        if ($('#res_name')) $('#res_name').textContent = data.name || '（未识别）';
        if ($('#res_skills')) $('#res_skills').textContent = (data.skills || []).slice(0, 12).join('、') || '（无）';
        if ($('#res_projects')) $('#res_projects').textContent = (data.projects || []).length;
        if ($('#res_text')) $('#res_text').textContent = (data.raw_text || '').slice(0, 1500);
        const card = $('#resumeParsedCard');
        if (card) card.classList.remove('hidden');
        toast('简历解析完成 ✅', 'success');
      } catch (e) {
        toast('解析结果读取失败：' + e, 'error');
      } finally {
        if (wrap) wrap.classList.add('hidden');
      }
    };
    xhr.onerror = () => {
      toast('上传失败，网络错误或服务不可达', 'error');
      if (wrap) wrap.classList.add('hidden');
    };
    xhr.timeout = 60 * 1000;
    xhr.ontimeout = () => toast('上传超时，1 分钟内无响应', 'error');
    xhr.send(fd);
  }

  async function onGenerateStart() {
    const btn = $('#generateBtn');
    const label = $('#genBtnText');
    const spin = $('#genSpinner');
    if (btn) btn.disabled = true;
    if (spin) spin.classList.remove('hidden');
    if (label) label.textContent = '正在生成题库…';

    try {
      const jdText = ($('#jdText')?.value || '').trim();
      if (jdText.length < 20) {
        toast('JD 内容过短，请至少 20 字', 'warn');
        return;
      }
      state.jdText = jdText;

      if (!state.resume) {
        state.resume = {
          raw_text: '（未上传简历，按 JD 通用题目演示）',
          name: '', skills: [], projects: [], experiences: [], education: [],
        };
        toast('未上传简历：演示模式将按 JD 通用题目进行', 'warn', 4200);
      }

      const count = parseInt($('#questionCount')?.value || '7', 10);
      const fd = new FormData();
      fd.append('resume_text', state.resume.raw_text || '');
      fd.append('name', state.resume.name || '');
      fd.append('skills', (state.resume.skills || []).join('|'));
      fd.append('projects', (state.resume.projects || []).join('||'));
      fd.append('jd_text', jdText);
      fd.append('count', String(count));

      const resp = await fetch('/api/questions/generate', { method: 'POST', body: fd });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || data.ok === false) {
        toast('题库生成失败：' + (data.error || resp.statusText), 'error');
        return;
      }
      state.questions = data.questions || [];
      state.questionsRaw = JSON.parse(JSON.stringify(state.questions));
      state.position = data.position || '';
      if ($('#jd_position')) $('#jd_position').textContent = state.position;
      const dims = state.questions.map(q => q.dimension).filter((v, i, a) => a.indexOf(v) === i);
      if ($('#jd_skills')) $('#jd_skills').textContent = dims.join(' · ');
      if ($('#jd_kps')) $('#jd_kps').textContent = state.questions.slice(0, 5).map(q => q.dimension).join(' · ') + ' …';
      const ol = $('#questionsList');
      if (ol) {
        ol.innerHTML = '';
        state.questions.forEach((q) => {
          const li = document.createElement('li');
          li.className = 'pl-1 py-0.5';
          li.innerHTML =
            `<div class="inline-flex items-center gap-1">
              <span class="text-xs px-2 py-0.5 rounded-md bg-primary-50 text-primary-700">${escapeHtml(q.dimension)}</span>
              <span>${escapeHtml(q.question)}</span>
            </div>
            ${q.hint ? `<div class="text-[12px] text-slate-400 mt-0.5 ml-5">💡 提示：${escapeHtml(q.hint)}</div>` : ''}`;
          ol.appendChild(li);
        });
      }
      const card = $('#jdParsedCard');
      if (card) card.classList.remove('hidden');

      await createInterviewSession();
    } catch (e) {
      console.error(e);
      showModalErr('题库生成异常', e && e.message ? e.message : String(e));
    } finally {
      if (btn) btn.disabled = false;
      if (spin) spin.classList.add('hidden');
      if (label) label.textContent = '3 · 生成题库并开始面试（结果写入 MySQL）';
    }
  }

  async function createInterviewSession() {
    const fd = new FormData();
    fd.append('resume_text', state.resume.raw_text || '');
    fd.append('jd_text', state.jdText);
    fd.append('position', state.position || '');
    fd.append('questions_json', JSON.stringify(state.questionsRaw || []));
    fd.append('name', state.resume.name || '');
    fd.append('skills', (state.resume.skills || []).join('|'));
    if (state.user && state.user.id) fd.append('user_id', String(state.user.id));

    const resp = await fetch('/api/session/start', { method: 'POST', body: fd });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || data.ok === false) {
      toast('会话创建失败：' + (data.error || resp.statusText), 'error');
      return;
    }
    state.sessionId = data.session_id;
    state.position = data.position;
    state.welcome = data.welcome;
    state.totalRounds = data.total_rounds || state.questions.length;
    state.round = 0;
    state.interviewing = true;
    toast('面试已开始 🚀，祝你发挥出色', 'success');

    switchTab('interview');
    resetChat();
    appendBubble('interviewer', state.welcome, { ts: Date.now() });
    const info = await fetch(`/api/session/${state.sessionId}`).then(r => r.json()).catch(() => ({}));
    if (info.current_question) {
      const first = info.current_question.question +
        (info.current_question.hint ? `\n\n💡 提示：${info.current_question.hint}` : '');
      appendBubble('interviewer', first, { ts: Date.now() + 1, stream: true, dim: info.current_question.dimension });
    }
    updateSessionTopbar(info);
  }

  // ========== 视图 2：Interview ==========
  function initInterview() {
    const ta = $('#answerInput');
    if (ta) {
      ta.addEventListener('input', () => {
        const cc = $('#answerCharCount');
        if (cc) cc.textContent = ta.value.length;
      });
      ta.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendAnswer();
        }
      });
    }
    const sendBtn = $('#sendBtn');
    if (sendBtn) sendBtn.addEventListener('click', sendAnswer);
    const endBtn = $('#endBtn');
    if (endBtn) endBtn.addEventListener('click', onEndInterview);
    const ttsBtn = $('#ttsToggle');
    if (ttsBtn) ttsBtn.addEventListener('click', () => {
      state.autoTTS = !state.autoTTS;
      toast('自动朗读：' + (state.autoTTS ? '已开启' : '已关闭'), 'info', 1500);
    });
    initMic();
  }

  function resetChat() {
    const cw = $('#chatWrap');
    if (cw) cw.innerHTML = '';
  }

  function appendBubble(role, content, opts = {}) {
    const cw = $('#chatWrap');
    if (!cw) return null;
    const row = document.createElement('div');
    if (role === 'candidate') row.className = 'bubble-row candidate';
    else if (role === 'system') row.className = 'bubble-row system';
    else row.className = 'bubble-row interviewer-row';

    const wrap = document.createElement('div');
    wrap.style.maxWidth = '100%';
    wrap.style.width = '100%';

    let header = '';
    if (role !== 'system') {
      const isInterviewer = role === 'interviewer';
      header = `<div class="flex items-center gap-1.5 mb-1 ${isInterviewer ? '' : 'justify-end'}">
        <span class="text-xs text-slate-500">${isInterviewer ? '🤖 AI 面试官' : '👤 你（候选人）'}</span>
        ${opts.dim ? `<span class="text-[11px] px-2 py-0.5 rounded-md bg-primary-50 text-primary-700">${escapeHtml(opts.dim)}</span>` : ''}
      </div>`;
    }

    const bubble = document.createElement('div');
    bubble.className = `bubble ${role}`;
    if (opts.stream) bubble.classList.add('typing-cursor');
    bubble.innerHTML = header + '<div class="bub-content whitespace-pre-wrap"></div>';
    const bubContent = bubble.querySelector('.bub-content');
    bubContent.textContent = content;
    wrap.appendChild(bubble);

    const meta = document.createElement('div');
    meta.className = 'bubble-meta';
    if (role === 'interviewer') {
      meta.classList.add('justify-start');
      const ttsBtn = document.createElement('button');
      ttsBtn.className = 'bubble-tts';
      ttsBtn.type = 'button';
      ttsBtn.textContent = '🔊 朗读';
      ttsBtn.addEventListener('click', () => speak(bubContent.textContent || content));
      meta.appendChild(ttsBtn);
      if (opts.ts) {
        const t = document.createElement('span');
        t.textContent = new Date(opts.ts).toLocaleTimeString('zh-CN', { hour12: false });
        meta.appendChild(t);
      }
    } else if (role === 'candidate') {
      meta.classList.add('justify-end');
      if (opts.ts) {
        const t = document.createElement('span');
        t.textContent = new Date(opts.ts).toLocaleTimeString('zh-CN', { hour12: false });
        meta.appendChild(t);
      }
    } else {
      meta.classList.add('justify-center');
    }
    wrap.appendChild(meta);
    row.appendChild(wrap);
    cw.appendChild(row);
    scrollChatBottom();

    if (role === 'interviewer' && state.autoTTS && !opts.silent && (bubContent.textContent || content).trim()) {
      if (!opts.stream) speak(bubContent.textContent || content);
    }
    return { bubble, contentEl: bubContent };
  }

  function scrollChatBottom() {
    const cw = $('#chatWrap');
    if (cw) requestAnimationFrame(() => { cw.scrollTop = cw.scrollHeight; });
  }

  function speak(text) {
    try {
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text || '');
      u.lang = 'zh-CN';
      u.rate = 1.0;
      u.pitch = 1;
      window.speechSynthesis.speak(u);
    } catch (_) {}
  }

  function initMic() {
    const btn = $('#micBtn');
    if (!btn) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      btn.title = '当前浏览器不支持语音识别，请改用 Chrome/Edge 并在 localhost 或 https 访问';
      btn.addEventListener('click', () => toast('当前环境不支持浏览器语音识别（需 Chrome/Edge + localhost/https）', 'warn', 5000));
      return;
    }
    let recog, holding = false;
    const startRec = () => {
      try {
        recog = new SR();
        recog.lang = 'zh-CN';
        recog.interimResults = true;
        recog.continuous = false;
        let finalText = '';
        recog.onresult = (ev) => {
          let tmp = '';
          for (let i = ev.resultIndex; i < ev.results.length; i++) {
            const r = ev.results[i];
            if (r.isFinal) finalText += r[0].transcript;
            else tmp += r[0].transcript;
          }
          const ta = $('#answerInput');
          if (ta) { ta.value = finalText + tmp; $('#answerCharCount').textContent = ta.value.length; }
        };
        recog.onerror = () => {
          holding = false;
          btn.classList.remove('animate-pulseSoft', 'bg-ai-500', 'text-white');
        };
        recog.onend = () => {
          holding = false;
          btn.classList.remove('animate-pulseSoft', 'bg-ai-500', 'text-white');
        };
        recog.start();
      } catch (e) {
        toast('启动语音识别失败：' + e.message, 'error');
      }
    };
    const startHold = (e) => {
      e.preventDefault();
      if (holding) return;
      holding = true;
      btn.classList.add('animate-pulseSoft', 'bg-ai-500', 'text-white');
      startRec();
    };
    const endHold = () => {
      if (!holding) return;
      holding = false;
      try { if (recog) recog.stop(); } catch (_) {}
      setTimeout(() => btn.classList.remove('animate-pulseSoft', 'bg-ai-500', 'text-white'), 200);
    };
    btn.addEventListener('mousedown', startHold);
    btn.addEventListener('mouseup', endHold);
    btn.addEventListener('mouseleave', () => { if (holding) endHold(); });
    btn.addEventListener('touchstart', startHold, { passive: false });
    btn.addEventListener('touchend', endHold);
    btn.addEventListener('touchcancel', endHold);
    btn.title = '🎙️ 按住说话（需 Chrome/Edge + localhost 或 HTTPS）';
  }

  async function sendAnswer() {
    if (!state.sessionId) return toast('会话尚未创建，请先在第 1 步生成题库', 'warn');
    if (!state.interviewing) return toast('面试已结束，请前往报告页', 'warn');

    const ta = $('#answerInput');
    const text = (ta?.value || '').trim();
    if (!text) return toast('回答内容不能为空', 'warn');
    appendBubble('candidate', text, { ts: Date.now() });
    if (ta) { ta.value = ''; $('#answerCharCount').textContent = '0'; }

    const sendBtn = $('#sendBtn');
    if (sendBtn) sendBtn.disabled = true;
    $('#sendSpinner')?.classList.remove('hidden');
    const sl = $('#sendLabel');
    if (sl) sl.textContent = '回复中…';

    try {
      const postResp = await fetch(`/api/session/${state.sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: text }),
      });
      const data = await postResp.json().catch(() => ({}));
      if (!postResp.ok || data.ok === false) {
        toast(data.error || `请求失败：${postResp.status}`, 'error');
        if ((data.error || '').indexOf('已结束') >= 0) return goEvaluate();
        return;
      }

      const finished = !!data.finished;
      const nextText = (data.next_question || (finished ? '面试已结束，稍后将为你生成报告。' : '')).toString();
      const dim = data.current_question && data.current_question.dimension;

      const refs = appendBubble('interviewer', '', { ts: Date.now(), stream: true, dim, silent: true });
      await streamAndRender(refs ? refs.contentEl : null, nextText, finished);

      const info = await fetch(`/api/session/${state.sessionId}`).then(r => r.json()).catch(() => ({}));
      updateSessionTopbar(info);

      if (finished) {
        state.interviewing = false;
        toast('面试结束，正在生成报告…', 'info', 2200);
        await goEvaluate();
      }
    } catch (e) {
      console.error(e);
      toast('对话异常：' + (e.message || e), 'error');
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      $('#sendSpinner')?.classList.add('hidden');
      if (sl) sl.textContent = '发送';
      if (ta) ta.focus();
    }
  }

  async function streamAndRender(contentEl, text, finished) {
    if (!contentEl) {
      // 兜底：直接渲染
      appendBubble('interviewer', text || '', { ts: Date.now() });
      return;
    }
    try {
      const url = `/api/session/${encodeURIComponent(state.sessionId)}/stream?text=${encodeURIComponent(text || '')}`;
      const resp = await fetch(url, { headers: { 'Accept': 'text/event-stream' } });
      if (!resp.ok || !resp.body) throw new Error('SSE 流请求失败');
      const reader = resp.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        // 逐行扫描 data: 前缀（禁止 split('\n\n')，避免粘包/分片 JSON.parse 失败）
        while ((idx = buffer.indexOf('\n')) >= 0) {
          const rawLine = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 1);
          const line = rawLine.replace(/\r$/, '').trim();
          if (!line) continue;
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (!payload || payload === '[DONE]') continue;
          try {
            const obj = JSON.parse(payload);
            if (obj.chunk) {
              contentEl.textContent += obj.chunk;
              scrollChatBottom();
            }
            if (obj.done) {
              const pb = contentEl.closest && contentEl.closest('.bubble');
              if (pb) pb.classList.remove('typing-cursor');
              if (state.autoTTS) speak(contentEl.textContent);
            }
          } catch (_) {}
        }
      }
      const pb = contentEl.closest && contentEl.closest('.bubble');
      if (pb) pb.classList.remove('typing-cursor');
      if (state.autoTTS) speak(contentEl.textContent || text);
    } catch (e) {
      contentEl.textContent = text || '';
      const pb = contentEl.closest && contentEl.closest('.bubble');
      if (pb) pb.classList.remove('typing-cursor');
      scrollChatBottom();
      if (state.autoTTS) speak(text || '');
    }
  }

  function updateSessionTopbar(info) {
    const total = Math.max(1, info.total_questions || state.totalRounds || state.questions.length || 1);
    const cur = Math.min(total, Math.max(0, (info.current_idx ?? 0)) + 1);
    const follow = info.followup_count || 0;
    state.round = info.round || state.round;
    state.totalRounds = total;
    const si = $('#sessionInfo');
    if (si) si.textContent = `${state.position || '定制面试'} · 会话号 ${String(state.sessionId || '').slice(-6)}`;
    const ri = $('#roundInfo');
    if (ri) ri.textContent = follow > 0 ? `${cur}/${total} · 追问 ${follow}` : `${cur}/${total}`;
    const pb = $('#progressBar');
    if (pb) pb.style.width = Math.min(100, (cur / total) * 100) + '%';
  }

  async function onEndInterview() {
    if (!state.sessionId) return toast('尚未开始', 'warn');
    if (!confirm('确定要结束本次面试吗？结束后系统会生成复盘报告。')) return;
    try {
      await fetch(`/api/session/${encodeURIComponent(state.sessionId)}/close?reason=${encodeURIComponent('用户主动结束')}`, { method: 'POST' });
      appendBubble('interviewer', '面试已结束，稍后为你生成多维度评估与改进建议。', { ts: Date.now() });
    } catch (_) {}
    state.interviewing = false;
    await goEvaluate();
  }

  // ========== 视图 3：History（MySQL 历史，容错降级）==========
  function initHistory() {
    const btn = $('#historyRefreshBtn');
    if (btn) btn.addEventListener('click', loadHistory);
  }

  async function loadHistory() {
    const host = $('#historyList');
    if (!host) return;
    host.innerHTML = '<div class="text-sm text-slate-400 py-6 text-center">加载中…</div>';
    const uid = state.user && state.user.id;
    if (!uid) {
      host.innerHTML = '<div class="text-sm text-slate-500 py-6 text-center">尚未确认身份。请先到「1 · 简历与岗位」页面点击「✅ 确认 / 注册身份」，再回来刷新。</div>';
      return;
    }
    try {
      const resp = await fetch(`/api/users/${encodeURIComponent(uid)}/sessions?page=1&size=20`);
      if (!resp.ok) throw new Error('http ' + resp.status);
      const data = await resp.json();
      const items = data.items || data.sessions || data || [];
      if (!Array.isArray(items) || items.length === 0) {
        host.innerHTML = '<div class="text-sm text-slate-500 py-6 text-center">暂无历史面试记录。完成一次模拟面试后这里会显示。</div>';
        return;
      }
      host.innerHTML = '';
      items.forEach((it) => {
        const card = document.createElement('div');
        card.className = 'history-card';
        const st = it.status || 'active';
        const badgeCls = { active: 'badge-active', finished: 'badge-finished', closed: 'badge-closed', expired: 'badge-expired' }[st] || 'badge-active';
        card.innerHTML = `
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="font-semibold">${escapeHtml(it.position || '定制面试')}</div>
            <span class="history-badge ${badgeCls}">${escapeHtml(st)}</span>
          </div>
          <div class="mt-1 text-xs text-slate-500">
            会话 ${escapeHtml(String(it.session_id || '').slice(-8))} ·
            轮次 ${it.total_rounds ?? it.round ?? 0} ·
            ${it.created_at ? new Date(it.created_at).toLocaleString('zh-CN') : ''}
            ${it.total_score ? ` · 得分 <b class="text-primary-700">${it.total_score}</b>（${escapeHtml(it.level || '')}）` : ''}
          </div>
          <div class="mt-2 flex gap-2">
            <button class="px-3 py-1 rounded-lg text-xs bg-primary-50 text-primary-700 hover:bg-primary-100" data-sid="${escapeHtml(it.session_id || '')}">查看报告</button>
          </div>`;
        const viewBtn = card.querySelector('button');
        if (viewBtn) viewBtn.addEventListener('click', () => viewHistoryReport(it.session_id));
        host.appendChild(card);
      });
    } catch (_) {
      host.innerHTML = '<div class="text-sm text-amber-600 py-6 text-center">历史接口尚未接入（后端 MySQL 路由待上线）。完成后端 /api/users/:uid/sessions 后这里将自动显示历史会话。</div>';
    }
  }

  async function viewHistoryReport(sid) {
    if (!sid) return;
    try {
      const resp = await fetch(`/api/sessions/${encodeURIComponent(sid)}/report`);
      if (!resp.ok) throw new Error('not ready');
      const data = await resp.json();
      renderReport(data);
      switchTab('result');
    } catch (_) {
      toast('该历史报告接口待后端接入 MySQL 后可用', 'warn', 3500);
    }
  }

  // ========== 视图 4：Result ==========
  async function goEvaluate() {
    if (!state.sessionId) return;
    switchTab('result');
    if ($('#r_total')) $('#r_total').textContent = '—';
    if ($('#r_level')) $('#r_level').textContent = '评估中…';
    if ($('#r_summary')) $('#r_summary').textContent = '正在读取对话全文，请稍候…';
    try {
      const resp = await fetch(`/api/evaluate/${encodeURIComponent(state.sessionId)}`, { method: 'POST' });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || (!data.total_score && data.total_score !== 0)) {
        toast(data.error || '评分服务异常，请稍后重试', 'error', 4500);
        return;
      }
      renderReport(data);
    } catch (e) {
      toast('评分失败：' + (e.message || e), 'error');
    }
  }

  function renderReport(data) {
    if ($('#r_level')) $('#r_level').textContent = data.level || '—';
    if ($('#r_summary')) $('#r_summary').textContent = data.transcript_summary || '';
    animateNumber($('#r_total'), data.total_score, 1400);

    const dimsHost = $('#r_dims');
    if (dimsHost) {
      dimsHost.innerHTML = '';
      (data.dimensions || []).forEach((d) => {
        const row = document.createElement('div');
        row.className = 'dim-row';
        row.innerHTML = `
          <div class="text-sm text-slate-600">${escapeHtml(d.dimension)}</div>
          <div>
            <div class="dim-bar-wrap"><div class="dim-bar-fill" data-target="${Number(d.score || 0)}"></div></div>
            <div class="mt-1 text-xs text-slate-500 leading-6">${escapeHtml(d.comment || '')}</div>
          </div>
          <div class="text-right font-semibold score-rolling text-lg text-slate-700" data-target="${Number(d.score || 0)}">0</div>`;
        dimsHost.appendChild(row);
      });
      setTimeout(() => {
        dimsHost.querySelectorAll('.dim-bar-fill').forEach((el) => {
          el.style.width = Math.max(0, Math.min(100, Number(el.dataset.target || 0))) + '%';
        });
        dimsHost.querySelectorAll('.score-rolling').forEach((el) => animateNumber(el, Number(el.dataset.target || 0), 1100));
      }, 120);
    }

    if ($('#r_highlights')) $('#r_highlights').textContent = data.highlights || '';
    if ($('#r_weaknesses')) $('#r_weaknesses').textContent = data.weaknesses || '';
    const sug = $('#r_suggestions');
    if (sug) {
      sug.innerHTML = '';
      (data.suggestions || []).forEach((s) => {
        const li = document.createElement('li');
        li.innerHTML = escapeHtml(s);
        sug.appendChild(li);
      });
    }
    const meta = $('#reportMeta');
    if (meta) meta.textContent =
      `${state.position || '定制面试'} · 共 ${state.totalRounds || 'N'} 题 · 生成时间 ${new Date().toLocaleString('zh-CN')}`;
  }

  function animateNumber(el, target, ms = 1200) {
    if (!el) return;
    const start = performance.now();
    const end = Math.max(0, Math.min(100, Math.round(Number(target) || 0)));
    function tick(now) {
      const p = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * eased);
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = end;
    }
    requestAnimationFrame(tick);
  }

  function initResult() {
    const again = $('#reportAgainBtn');
    if (again) again.addEventListener('click', () => {
      if (!confirm('确定开启新一轮模拟吗？当前会话与报告将从视图移除。')) return;
      state.sessionId = null; state.questions = []; state.questionsRaw = [];
      state.interviewing = false; state.totalRounds = 0; state.round = 0;
      $('#jdParsedCard')?.classList.add('hidden');
      switchTab('setup');
    });
    const print = $('#reportPrintBtn');
    if (print) print.addEventListener('click', () => window.print());
  }

  function bindNav() {
    $$('.nav-btn').forEach((b) => {
      b.addEventListener('click', () => {
        const tab = b.dataset.tab;
        if (tab === 'interview' && !state.sessionId) return toast('请先在第 1 步生成题库并开始面试', 'warn');
        if (tab === 'result' && !state.sessionId) return toast('还没有可查看的面试报告', 'warn');
        switchTab(tab);
      });
    });
    const close = $('#errCloseBtn');
    if (close) close.addEventListener('click', () => { const d = $('#errModal'); if (d && d.close) d.close(); });
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindNav();
    initUser();
    initSetup();
    initInterview();
    initHistory();
    initResult();
    switchTab('setup');
  });

})();
