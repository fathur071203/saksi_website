const page = document.body.dataset.page;

const escapeHtml = (value) => String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const formatInlineMarkdown = (text) => escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');

const renderMarkdown = (markdownText) => {
    const lines = String(markdownText || '').replace(/\r\n/g, '\n').split('\n');
    const html = [];
    let paragraphBuffer = [];
    let listType = null;

    const flushParagraph = () => {
        if (!paragraphBuffer.length) return;
        html.push(`<p>${formatInlineMarkdown(paragraphBuffer.join(' '))}</p>`);
        paragraphBuffer = [];
    };

    const closeList = () => {
        if (listType) {
            html.push(listType === 'ol' ? '</ol>' : '</ul>');
            listType = null;
        }
    };

    lines.forEach((rawLine) => {
        const line = rawLine.trim();

        if (!line) {
            flushParagraph();
            closeList();
            return;
        }

        const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
        if (headingMatch) {
            flushParagraph();
            closeList();
            const level = Math.min(headingMatch[1].length + 1, 4);
            html.push(`<h${level}>${formatInlineMarkdown(headingMatch[2])}</h${level}>`);
            return;
        }

        const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
        if (orderedMatch) {
            flushParagraph();
            if (listType !== 'ol') {
                closeList();
                html.push('<ol>');
                listType = 'ol';
            }
            html.push(`<li>${formatInlineMarkdown(orderedMatch[1])}</li>`);
            return;
        }

        const bulletMatch = line.match(/^[-*]\s+(.+)$/);
        if (bulletMatch) {
            flushParagraph();
            if (listType !== 'ul') {
                closeList();
                html.push('<ul>');
                listType = 'ul';
            }
            html.push(`<li>${formatInlineMarkdown(bulletMatch[1])}</li>`);
            return;
        }

        if (listType) {
            closeList();
        }
        paragraphBuffer.push(line);
    });

    flushParagraph();
    closeList();
    return html.join('');
};

const loadScript = (src) => new Promise((resolve, reject) => {
    if (!src) {
        reject(new Error('Script source is empty.'));
        return;
    }

    const existingScript = document.querySelector(`script[data-dynamic-src="${src}"]`);
    if (existingScript) {
        existingScript.addEventListener('load', () => resolve(src), { once: true });
        existingScript.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });

        if (existingScript.dataset.loaded === 'true') {
            resolve(src);
        }
        return;
    }

    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.dataset.dynamicSrc = src;
    script.addEventListener('load', () => {
        script.dataset.loaded = 'true';
        resolve(src);
    }, { once: true });
    script.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
    document.head.appendChild(script);
});

const ensureSocketIoClient = async () => {
    if (typeof window.io !== 'undefined') {
        return window.io;
    }

    const sources = Array.isArray(window.SAKSI_SOCKET_IO_SOURCES)
        ? window.SAKSI_SOCKET_IO_SOURCES
        : [];

    for (const source of sources) {
        try {
            await loadScript(source);
            if (typeof window.io !== 'undefined') {
                return window.io;
            }
        } catch (error) {
            console.warn('Socket.IO client load failed:', source, error);
        }
    }

    return null;
};

const sidebar = document.getElementById('app-sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebarClose = document.getElementById('sidebar-close');
const sidebarBackdrop = document.getElementById('sidebar-backdrop');
const sidebarLinks = document.querySelectorAll('[data-sidebar-link]');

const mobileSidebarEnabled = () => window.innerWidth < 1024;

const openSidebar = () => {
    if (!sidebar || !mobileSidebarEnabled()) return;

    sidebar.classList.remove('-translate-x-full');
    sidebar.setAttribute('aria-hidden', 'false');
    sidebarToggle?.setAttribute('aria-expanded', 'true');
    document.body.classList.add('overflow-hidden');

    if (sidebarBackdrop) {
        sidebarBackdrop.classList.remove('pointer-events-none', 'opacity-0');
        sidebarBackdrop.classList.add('pointer-events-auto', 'opacity-100');
        sidebarBackdrop.setAttribute('aria-hidden', 'false');
    }
};

const closeSidebar = () => {
    if (!sidebar) return;

    if (mobileSidebarEnabled()) {
        sidebar.classList.add('-translate-x-full');
        sidebar.setAttribute('aria-hidden', 'true');
        sidebarToggle?.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('overflow-hidden');

        if (sidebarBackdrop) {
            sidebarBackdrop.classList.add('pointer-events-none', 'opacity-0');
            sidebarBackdrop.classList.remove('pointer-events-auto', 'opacity-100');
            sidebarBackdrop.setAttribute('aria-hidden', 'true');
        }
        return;
    }

    sidebar.classList.remove('-translate-x-full');
    sidebar.setAttribute('aria-hidden', 'false');
    sidebarToggle?.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('overflow-hidden');
    if (sidebarBackdrop) {
        sidebarBackdrop.classList.add('pointer-events-none', 'opacity-0');
        sidebarBackdrop.classList.remove('pointer-events-auto', 'opacity-100');
        sidebarBackdrop.setAttribute('aria-hidden', 'true');
    }
};

sidebarToggle?.addEventListener('click', openSidebar);
sidebarClose?.addEventListener('click', closeSidebar);
sidebarBackdrop?.addEventListener('click', closeSidebar);
sidebarLinks.forEach((link) => link.addEventListener('click', closeSidebar));

window.addEventListener('resize', closeSidebar);

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeSidebar();
    }
});

closeSidebar();

const renderSearchResults = (results) => {
    const searchResults = document.getElementById('search-results');
    if (!searchResults) return;

    if (!results.length) {
        searchResults.innerHTML = '<div class="px-4 py-3 text-sm text-slate-500">Tidak ada hasil yang relevan.</div>';
        searchResults.classList.remove('hidden');
        return;
    }

    searchResults.innerHTML = results.map((item) => `
        <div class="border-b border-slate-100 px-4 py-3 last:border-b-0">
            <p class="text-xs uppercase tracking-[0.2em] text-prestigeGold">${item.type}</p>
            <p class="mt-1 text-sm font-semibold text-biNavy">${item.title}</p>
            <p class="mt-1 text-xs text-slate-500">${item.subtitle}</p>
        </div>
    `).join('');
    searchResults.classList.remove('hidden');
};

const globalSearch = document.getElementById('global-search');
globalSearch?.addEventListener('input', async (event) => {
    const keyword = event.target.value.trim();
    const searchResults = document.getElementById('search-results');

    if (!keyword) {
        searchResults?.classList.add('hidden');
        return;
    }

    const response = await fetch(`/api/search?q=${encodeURIComponent(keyword)}`);
    const payload = await response.json();
    renderSearchResults(payload.results || []);
});

document.addEventListener('click', (event) => {
    const target = event.target;
    const searchResults = document.getElementById('search-results');
    if (searchResults && !searchResults.contains(target) && target !== globalSearch) {
        searchResults.classList.add('hidden');
    }
});

const renderExperts = (experts) => {
    const body = document.getElementById('experts-table-body');
    if (!body) return;

    body.innerHTML = experts.map((expert) => {
        const badges = expert.badges.length
            ? expert.badges.map((badge) => `
            <span title="${badge.awarded_at} · ${badge.description}" class="cursor-help rounded-full border border-prestigeGold/40 bg-prestigeGold/10 px-3 py-1 text-xs font-semibold text-prestigeGold transition hover:-translate-y-0.5 hover:bg-prestigeGold hover:text-deepBlue">${badge.topic} · ${badge.level}</span>
        `).join('')
            : '<span class="rounded-full border border-slate-200 bg-cleanSlate px-3 py-1 text-xs font-semibold text-slate-500">Belum ada e-Badge</span>';

        const statusClass = expert.status === 'Available'
            ? 'bg-emerald-100 text-validGreen'
            : 'bg-amber-100 text-amber-700';

        return `
            <tr class="transition hover:bg-slate-50/80">
                <td class="px-6 py-5">
                    <p class="font-semibold text-slateInk">${expert.name}</p>
                    <p class="mt-1 text-xs text-slate-500">${expert.unit}</p>
                </td>
                <td class="px-6 py-5"><div class="flex flex-wrap gap-2">${badges}</div></td>
                <td class="px-6 py-5 font-semibold text-biNavy">${expert.courtroom_hours} jam</td>
                <td class="px-6 py-5">
                    <span class="rounded-full px-3 py-1 text-xs font-bold ${statusClass}">${expert.status}</span>
                    <p class="mt-2 text-xs text-slate-500">${expert.expertise_summary}</p>
                </td>
            </tr>
        `;
    }).join('');
};

const liviaAvatarMarkup = `
    <div class="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-deepBlue p-1 shadow-command">
        <img src="/static/robot-avatar.svg" alt="Avatar robot Livia" class="h-full w-full object-contain">
    </div>
`;

if (page === 'dashboard') {
    document.querySelectorAll('.topic-filter').forEach((button) => {
        button.addEventListener('click', async () => {
            const topic = button.dataset.topic;
            document.getElementById('dashboard-skeleton')?.classList.remove('hidden');
            const response = await fetch(`/dashboard/api/experts?topic=${encodeURIComponent(topic)}`);
            const payload = await response.json();
            renderExperts(payload.experts || []);
            document.getElementById('dashboard-skeleton')?.classList.add('hidden');

            document.querySelectorAll('.topic-filter').forEach((chip) => {
                chip.className = 'topic-filter rounded-full border border-slate-200 bg-cleanSlate px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-prestigeGold hover:text-biNavy';
            });
            button.className = 'topic-filter rounded-full border border-prestigeGold bg-prestigeGold px-4 py-2 text-sm font-semibold text-deepBlue transition';
        });
    });
}

const typeWriter = (element, text, speed = 24) => {
    if (!element) return;
    element.textContent = '';
    let index = 0;
    const timer = window.setInterval(() => {
        element.textContent += text.charAt(index);
        index += 1;
        if (index >= text.length) {
            clearInterval(timer);
        }
    }, speed);
};

if (page === 'interrogation') {
    const questionElement = document.getElementById('scenario-question');
    const answerElement = document.getElementById('interrogation-answer');
    const submitButton = document.getElementById('submit-answer');
    const transcriptBox = document.getElementById('transcript-box');
    const scoreContainer = document.getElementById('feedback-score');
    const scoreElement = scoreContainer?.querySelector('p:last-child');
    const verdictElement = document.getElementById('feedback-verdict');
    const coachingPrompt = document.getElementById('coaching-prompt');
    const strengthList = document.getElementById('strength-list');
    const riskList = document.getElementById('risk-list');
    const improvementList = document.getElementById('improvement-list');
    const timerBar = document.getElementById('stress-timer-bar');
    const submitStatus = document.getElementById('interrogation-submit-status');
    let socket = null;
    let timerHandle = null;
    let stressSeconds = 60;
    let activeScenario = {
        topic: document.querySelector('#scenario-question')?.dataset.topic || '',
        difficulty: document.querySelector('#scenario-question')?.dataset.difficulty || '',
        question: questionElement?.dataset.fullText || '',
        stress_seconds: 60,
    };

    const updateSubmitState = (state, message) => {
        if (submitStatus) {
            submitStatus.textContent = message;
            submitStatus.className = 'mt-4 rounded-2xl border px-4 py-3 text-sm';

            if (state === 'success') {
                submitStatus.classList.add('border-emerald-400/30', 'bg-emerald-500/10', 'text-emerald-200');
            } else if (state === 'error') {
                submitStatus.classList.add('border-red-400/30', 'bg-red-500/10', 'text-red-200');
            } else if (state === 'loading') {
                submitStatus.classList.add('border-prestigeGold/30', 'bg-prestigeGold/10', 'text-prestigeGold');
            } else {
                submitStatus.classList.add('border-white/10', 'bg-white/5', 'text-slate-300');
            }
        }

        if (submitButton) {
            submitButton.disabled = state === 'loading';
            submitButton.classList.toggle('opacity-70', state === 'loading');
            submitButton.classList.toggle('cursor-not-allowed', state === 'loading');
            submitButton.textContent = state === 'loading' ? 'Mengirim...' : 'Kirim ke Live Feedback';
        }
    };

    const startTimer = (totalSeconds) => {
        if (!timerBar) return;
        window.clearInterval(timerHandle);

        let remainingSeconds = totalSeconds;
        timerBar.style.width = '100%';

        timerHandle = window.setInterval(() => {
            remainingSeconds -= 1;
            const progress = Math.max((remainingSeconds / totalSeconds) * 100, 0);
            timerBar.style.width = `${progress}%`;

            if (remainingSeconds <= 0) {
                window.clearInterval(timerHandle);
            }
        }, 1000);
    };

    const applyScenario = (scenario) => {
        if (!questionElement) return;
        activeScenario = { ...scenario };
        questionElement.dataset.fullText = scenario.question;
        typeWriter(questionElement, scenario.question, 18);
        stressSeconds = scenario.stress_seconds;
        startTimer(stressSeconds);
    };

    applyScenario({
        topic: activeScenario.topic,
        difficulty: activeScenario.difficulty,
        question: questionElement.dataset.fullText,
        stress_seconds: 60
    });
    updateSubmitState('loading', 'Menghubungkan Live Feedback ke server...');

    const initializeLiveFeedback = async () => {
        const ioFactory = await ensureSocketIoClient();
        if (!ioFactory) {
            updateSubmitState('error', 'Live Feedback belum aktif karena library Socket.IO gagal dimuat di browser ini.');
            return;
        }

        socket = ioFactory({ transports: ['polling', 'websocket'] });

        socket.on('connect', () => {
            updateSubmitState('idle', 'Terhubung ke Live Feedback. Silakan kirim jawaban untuk dievaluasi AI.');
        });

        socket.on('disconnect', () => {
            updateSubmitState('error', 'Koneksi Live Feedback terputus. Muat ulang halaman atau coba lagi.');
        });

        socket.on('connect_error', () => {
            updateSubmitState('error', 'Gagal terhubung ke Live Feedback. Pastikan server aktif dan coba lagi.');
        });

        socket.on('transcription_update', (payload) => {
            transcriptBox.textContent = payload.transcript;
        });

        socket.on('feedback_update', (payload) => {
            scoreElement.textContent = payload.score;
            verdictElement.textContent = payload.verdict;
            verdictElement.className = payload.score >= 80
                ? 'rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-validGreen'
                : payload.score >= 60
                    ? 'rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-700'
                    : 'rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-dangerCrimson';
            transcriptBox.innerHTML = payload.highlighted_transcript;
            coachingPrompt.textContent = payload.coaching_prompt;
            strengthList.innerHTML = payload.strengths.map((item) => `<li class="rounded-2xl bg-emerald-50 px-4 py-3">✅ ${item}</li>`).join('');
            riskList.innerHTML = payload.risks.map((item) => `<li class="rounded-2xl bg-red-50 px-4 py-3">⚠️ ${item}</li>`).join('');
            improvementList.innerHTML = (payload.improvement_points || []).map((item) => `<li class="rounded-2xl bg-blue-50 px-4 py-3">🧭 ${item}</li>`).join('') || '<li class="rounded-2xl bg-slate-50 px-4 py-3">Tidak ada masukan tambahan yang mendesak pada jawaban ini.</li>';
            updateSubmitState('success', `Live Feedback berhasil diproses. Skor ${payload.score} dengan status ${payload.verdict}.`);
        });
    };

    initializeLiveFeedback();

    document.getElementById('new-scenario-button')?.addEventListener('click', async () => {
        const response = await fetch('/interrogation/api/scenario');
        const scenario = await response.json();
        applyScenario(scenario);
    });

    document.getElementById('load-sample-answer')?.addEventListener('click', () => {
        answerElement.value = 'Berdasarkan PBI No. 24/7/PBI/2022 Pasal 42 ayat (1) dan PBI No. 19/10/PBI/2017 Pasal 18 ayat (1), penyelenggara wajib melakukan identifikasi, verifikasi, serta pemantauan atas transaksi mencurigakan, termasuk pola smurfing di bawah threshold. Dalam kapasitas ahli Bank Indonesia, saya menerangkan adanya kewajiban kepatuhan administratif dan pelaporan, sedangkan pembuktian unsur pidana tetap menjadi kewenangan APH.';
    });

    document.getElementById('simulate-mic')?.addEventListener('click', () => {
        answerElement.focus();
        answerElement.classList.add('ring-4', 'ring-prestigeGold/20');
        setTimeout(() => answerElement.classList.remove('ring-4', 'ring-prestigeGold/20'), 900);
    });

    submitButton?.addEventListener('click', () => {
        const answer = answerElement.value.trim();
        if (!answer) {
            updateSubmitState('error', 'Isi jawaban terlebih dahulu sebelum dikirim ke Live Feedback.');
            answerElement.focus();
            return;
        }
        if (!socket || !socket.connected) {
            updateSubmitState('error', 'Live Feedback belum terhubung ke server. Coba reload halaman.');
            return;
        }

        updateSubmitState('loading', 'Jawaban berhasil dikirim. AI sedang membuat transkripsi dan evaluasi...');
        socket.emit('submit_answer', { answer, scenario: activeScenario });
    });
}

if (page === 'legal') {
    const scenarioInput = document.getElementById('legal-scenario');
    const outputPanel = document.getElementById('legal-output');
    const scenarioPreview = document.getElementById('legal-scenario-preview');
    const generateButton = document.getElementById('generate-brief');
    const chatResponseBox = document.getElementById('chatbot-response');
    const chatProviderBadge = document.getElementById('chat-provider-badge');
    const chatbotLoadingLabel = document.getElementById('chatbot-loading-label');
    const uploadStatus = document.getElementById('upload-status');
    const documentsList = document.getElementById('documents-list');
    const documentsCount = document.getElementById('documents-count');
    const insertDemoCaseButton = document.getElementById('insert-demo-case');
    const legalSampleNote = document.getElementById('legal-sample-note');

    const renderDocuments = (documents) => {
        documentsCount.textContent = `${documents.length} dokumen`;
        if (!documents.length) {
            documentsList.innerHTML = '<div class="rounded-3xl border border-slate-200 bg-white p-4 text-sm text-slate-500">Belum ada dokumen yang di-upload. Setelah diproses, chunk dokumen akan ikut dibaca oleh RAG/Gemini.</div>';
            return;
        }

        documentsList.innerHTML = documents.map((doc) => `
            <div class="rounded-3xl border border-slate-200 bg-white p-4">
                <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                        <p class="font-semibold text-slateInk">${doc.original_name}</p>
                        <p class="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">${doc.file_type} · ${doc.uploaded_at}</p>
                    </div>
                    <span class="rounded-full px-3 py-1 text-xs font-bold ${doc.status === 'processed' ? 'bg-emerald-100 text-validGreen' : 'bg-red-100 text-dangerCrimson'}">${doc.status}</span>
                </div>
                <div class="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-3">
                    <p>Word count: <span class="font-semibold text-slate-700">${doc.word_count}</span></p>
                    <p>Chunk count: <span class="font-semibold text-slate-700">${doc.chunk_count}</span></p>
                    <p>Chars: <span class="font-semibold text-slate-700">${doc.character_count || '-'}</span></p>
                </div>
                <p class="mt-2 text-xs text-slate-500">Path: <span class="font-semibold text-slate-700">${doc.raw_path}</span></p>
                <p class="mt-3 text-sm text-slate-600">${doc.note}</p>
            </div>
        `).join('');
    };

    const fetchDocuments = async () => {
        const response = await fetch('/legal-brief/api/documents');
        const payload = await response.json();
        renderDocuments(payload.documents || []);
    };

    insertDemoCaseButton?.addEventListener('click', async () => {
        insertDemoCaseButton.disabled = true;
        const previousLabel = insertDemoCaseButton.textContent;
        insertDemoCaseButton.textContent = 'Menyusun Contoh...';

        try {
            const response = await fetch('/legal-brief/api/sample-case');
            const payload = await response.json();

            if (!response.ok) {
                throw new Error(payload.error || 'Gagal menyusun contoh kasus.');
            }

            scenarioInput.value = payload.scenario || '';
            if (legalSampleNote) {
                const references = Array.isArray(payload.references) && payload.references.length
                    ? `<p><span class="font-semibold text-biNavy">Rujukan awal:</span><br>${payload.references.map((item) => `• ${formatInlineMarkdown(item)}`).join('<br>')}</p>`
                    : '<p>Contoh kasus berhasil disusun dari knowledge base lokal.</p>';
                legalSampleNote.innerHTML = references;
            }
        } catch (error) {
            scenarioInput.value = 'APH meminta keterangan ahli Bank Indonesia atas dugaan transaksi valas pada KUPVA BB senilai ekuivalen Rp2 miliar tanpa underlying yang jelas. Ditemukan indikasi transaksi dipecah di bawah threshold, kelemahan identifikasi dan verifikasi pengguna jasa, serta dugaan keterlambatan pelaporan transaksi mencurigakan. Mohon susun materi jawaban ahli BI dengan dasar hukum yang paling relevan, batas kewenangan BI, dan kutipan pasal yang dapat dibacakan saat pemeriksaan.';
            if (legalSampleNote) {
                legalSampleNote.innerHTML = '<p>Contoh fallback dimasukkan. Untuk hasil paling presisi, tambahkan atau perbarui regulasi di knowledge base lokal.</p>';
            }
        } finally {
            insertDemoCaseButton.disabled = false;
            insertDemoCaseButton.textContent = previousLabel;
        }
    });

    const renderRegulations = (items) => {
        document.getElementById('regulations-content').innerHTML = items.map((item) => `
            <article class="rounded-[1.25rem] border border-slate-200 bg-white p-4">
                <h3 class="text-sm font-bold leading-6 text-biNavy">${item.title}</h3>
                <div class="mt-2 text-sm leading-7 text-slate-700 whitespace-pre-line">${formatInlineMarkdown(String(item.body || '')).replace(/\n/g, '<br>')}</div>
            </article>
        `).join('');
    };

    const renderList = (targetId, items, emoji) => {
        document.getElementById(targetId).innerHTML = items.map((item) => `
            <div class="rounded-[1.25rem] border border-slate-200 bg-white p-4 text-sm leading-7 text-slate-700">${emoji} ${formatInlineMarkdown(String(item || ''))}</div>
        `).join('');
    };

    generateButton?.addEventListener('click', async () => {
        const scenario = scenarioInput.value.trim();
        if (!scenario) {
            scenarioInput.focus();
            return;
        }

        generateButton.disabled = true;
        generateButton.innerHTML = '<span class="inline-flex items-center gap-2"><span class="loading-dot"></span><span>Generating...</span></span>';
        outputPanel.classList.remove('hidden');
        scenarioPreview.textContent = scenario;
        outputPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        document.getElementById('brief-provider').textContent = 'Gemini / engine sedang memproses...';
        document.getElementById('regulations-content').innerHTML = '<div class="loading-panel"><span class="loading-dot"></span><span>Menarik peraturan, nomor, tanggal, pasal, dan kutipan ayat yang relevan...</span></div>';
        document.getElementById('bap-content').innerHTML = '<div class="loading-panel"><span class="loading-dot"></span><span>Menyusun draft jawaban BAP yang siap dibacakan...</span></div>';
        document.getElementById('traps-content').innerHTML = '<div class="loading-panel"><span class="loading-dot"></span><span>Menyiapkan antisipasi pertanyaan jebakan...</span></div>';

        const response = await fetch('/legal-brief/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario })
        });
        const payload = await response.json();

        if (!response.ok) {
            document.getElementById('brief-provider').textContent = payload.error || 'Gagal membuat legal brief.';
            document.getElementById('regulations-content').innerHTML = `<div class="rounded-3xl border border-red-200 bg-red-50 p-5 text-sm leading-7 text-red-700">${formatInlineMarkdown(payload.error || 'Gagal membuat legal brief.')}</div>`;
            document.getElementById('bap-content').innerHTML = '';
            document.getElementById('traps-content').innerHTML = '';
            generateButton.disabled = false;
            generateButton.textContent = 'Generate Brief';
            return;
        }

        document.getElementById('arch-ingestion').textContent = payload.retrieval_architecture.ingestion;
        document.getElementById('arch-retrieval').textContent = payload.retrieval_architecture.retrieval;
        document.getElementById('arch-generation').textContent = payload.retrieval_architecture.generation;
        document.getElementById('brief-provider').textContent = payload.provider_status || payload.provider || 'Context Retrieval Successful';
        renderRegulations(payload.regulations || []);
        renderList('bap-content', [...(payload.bap_draft || []), payload.disclaimer], '•');
        renderList('traps-content', payload.trap_questions || [], '🛡️');

        generateButton.disabled = false;
        generateButton.textContent = 'Generate Brief';
    });

    document.querySelectorAll('.copy-trigger').forEach((button) => {
        button.addEventListener('click', async () => {
            const target = document.getElementById(button.dataset.copyTarget);
            await navigator.clipboard.writeText(target.innerText.trim());
            button.textContent = 'Copied';
            setTimeout(() => {
                button.textContent = 'Copy';
            }, 1400);
        });
    });

    document.getElementById('insert-demo-chat')?.addEventListener('click', () => {
        document.getElementById('chatbot-prompt').value = 'Jelaskan batas wewenang BI sebagai saksi ahli pada perkara KUPVA BB yang diduga terkait TPPU dan pola smurfing.';
    });

    document.getElementById('send-chatbot-prompt')?.addEventListener('click', async () => {
        const promptInput = document.getElementById('chatbot-prompt');
        const prompt = promptInput.value.trim();
        if (!prompt) {
            promptInput.focus();
            return;
        }

        chatResponseBox.innerHTML = '<div class="loading-panel"><span class="loading-dot"></span><span>Livia / engine sedang menyusun jawaban...</span></div>';
        chatbotLoadingLabel?.classList.remove('hidden');
        chatbotLoadingLabel?.classList.add('flex');
        chatProviderBadge.textContent = 'Processing';
        const sendButton = document.getElementById('send-chatbot-prompt');
        sendButton.disabled = true;
        sendButton.innerHTML = '<span class="inline-flex items-center gap-2"><span class="loading-dot"></span><span>Processing...</span></span>';

        const response = await fetch('/legal-brief/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const payload = await response.json();

        chatbotLoadingLabel?.classList.add('hidden');
        chatbotLoadingLabel?.classList.remove('flex');
        sendButton.disabled = false;
        sendButton.textContent = 'Kirim ke Chatbot';

        if (!response.ok) {
            chatResponseBox.innerHTML = `<div class="chat-markdown"><p>${formatInlineMarkdown(payload.error || 'Gagal mendapatkan jawaban chatbot.')}</p></div>`;
            chatProviderBadge.textContent = 'Error';
            return;
        }

        chatResponseBox.innerHTML = `<div class="chat-markdown">${renderMarkdown(payload.reply)}</div>`;
        chatProviderBadge.textContent = payload.provider_status || payload.provider || 'Completed';
    });

    document.getElementById('refresh-documents')?.addEventListener('click', fetchDocuments);

    document.getElementById('upload-regulation')?.addEventListener('click', async () => {
        const fileInput = document.getElementById('regulation-upload');
        const file = fileInput.files?.[0];
        if (!file) {
            fileInput.focus();
            return;
        }

        uploadStatus.textContent = 'Meng-upload dan mengekstrak dokumen secara penuh tanpa memotong isi teks...';
        const formData = new FormData();
        formData.append('document', file);

        const response = await fetch('/legal-brief/api/documents', {
            method: 'POST',
            body: formData,
        });
        const payload = await response.json();

        if (!response.ok) {
            uploadStatus.textContent = payload.error || 'Gagal memproses dokumen.';
            return;
        }

        uploadStatus.textContent = `Berhasil: ${payload.original_name} diproses penuh menjadi ${payload.chunk_count} chunk (${payload.character_count || '-'} karakter) dan siap dipakai AI.`;
        fileInput.value = '';
        await fetchDocuments();
    });

    fetchDocuments();
}

if (page === 'livia') {
    const liviaThread = document.getElementById('livia-chat-thread');
    const liviaScroll = document.getElementById('livia-chat-scroll');
    const liviaInput = document.getElementById('livia-input');
    const liviaSend = document.getElementById('livia-send');
    const liviaStatus = document.getElementById('livia-status');
    const liviaProviderBadge = document.getElementById('livia-provider-badge');
    const liviaClear = document.getElementById('livia-clear-chat');
    const liviaCitationPopover = document.getElementById('livia-citation-popover');
    const liviaCitationBackdrop = document.getElementById('livia-citation-backdrop');
    const liviaCitationPanel = document.getElementById('livia-citation-panel');
    const liviaCitationBody = document.getElementById('livia-citation-body');
    const liviaCitationClose = document.getElementById('livia-citation-close');
    const storageKey = 'saksi-livia-thread';

    const renderCitationCards = (citations = []) => {
        if (!citations.length) {
            return '<div class="rounded-[1rem] border border-slate-200 bg-cleanSlate p-4 text-sm text-slate-500">Rujukan spesifik belum tersedia untuk jawaban ini.</div>';
        }

        return citations.map((citation) => `
            <article class="rounded-[1rem] border border-slate-200 bg-cleanSlate p-4">
                <div class="flex flex-wrap items-center gap-2">
                    <span class="rounded-full bg-biNavy px-3 py-1 text-xs font-bold text-white">${escapeHtml(citation.instrument_type || 'Dokumen')}</span>
                    <span class="text-sm font-bold text-biNavy">${escapeHtml(citation.code || '-')}</span>
                </div>
                <p class="mt-3 text-sm font-semibold leading-6 text-slateInk">${escapeHtml(citation.title || 'Judul tidak tersedia')}</p>
                <div class="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                    <p><span class="font-semibold text-slateInk">Nomor/Tahun:</span> ${escapeHtml(citation.number_year || '-')}</p>
                    <p><span class="font-semibold text-slateInk">Tanggal penetapan:</span> ${escapeHtml(citation.issued_date || '-')}</p>
                    <p><span class="font-semibold text-slateInk">Pasal/Ayat:</span> ${escapeHtml(citation.article || '-')}</p>
                    <p><span class="font-semibold text-slateInk">Bunyi norma:</span> ${escapeHtml(citation.quote || '-')}</p>
                </div>
            </article>
        `).join('');
    };

    const openCitationPopover = (citations = []) => {
        if (!liviaCitationPopover || !liviaCitationBody || !liviaCitationBackdrop || !liviaCitationPanel) return;
        liviaCitationBody.innerHTML = renderCitationCards(citations);
        liviaCitationPopover.classList.remove('hidden');
        liviaCitationPopover.classList.add('pointer-events-auto');
        requestAnimationFrame(() => {
            liviaCitationBackdrop.classList.add('opacity-100');
            liviaCitationPanel.classList.add('opacity-100');
        });
    };

    const closeCitationPopover = () => {
        if (!liviaCitationPopover || !liviaCitationBackdrop || !liviaCitationPanel) return;
        liviaCitationBackdrop.classList.remove('opacity-100');
        liviaCitationPanel.classList.remove('opacity-100');
        window.setTimeout(() => {
            liviaCitationPopover.classList.add('hidden');
            liviaCitationPopover.classList.remove('pointer-events-auto');
        }, 180);
    };

    const normalizeThreadMessage = (message) => {
        const role = message?.role === 'user' ? 'user' : 'assistant';
        const content = String(message?.content || '').trim();
        const meta = String(message?.meta || '').trim();
        const citations = Array.isArray(message?.citations) ? message.citations : [];

        if (!content) {
            return null;
        }

        return { role, content, meta, citations };
    };

    const renderMessage = ({ role, content, meta, citations = [] }) => {
        const isAssistant = role === 'assistant';
        const hasCitations = isAssistant && Array.isArray(citations) && citations.length > 0;
        const wrapper = document.createElement('article');
        wrapper.dataset.role = role;
        wrapper.dataset.content = content || '';
        wrapper.dataset.meta = meta || '';
        wrapper.dataset.citations = JSON.stringify(citations || []);
        wrapper.className = `flex items-start gap-4 ${isAssistant ? '' : 'justify-end'}`;
        wrapper.innerHTML = isAssistant
            ? `
                ${liviaAvatarMarkup}
                <div class="max-w-3xl rounded-[1.25rem] border border-slate-200 bg-white px-4 py-4 text-sm leading-7 text-slate-700 shadow-sm">
                    <div class="livia-markdown chat-markdown">${renderMarkdown(content)}</div>
                    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3">
                        ${meta ? `<div class="text-xs font-semibold text-prestigeGold">${escapeHtml(meta)}</div>` : '<div></div>'}
                        ${hasCitations ? '<button type="button" class="livia-citation-trigger rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-prestigeGold hover:text-biNavy">Rujukan</button>' : ''}
                    </div>
                </div>
            `
            : `
                <div class="max-w-3xl rounded-[1.25rem] bg-biNavy px-4 py-4 text-sm leading-7 text-white shadow-command">
                    <div class="livia-markdown chat-markdown text-white"><p>${formatInlineMarkdown(content).replace(/\n/g, '<br>')}</p></div>
                </div>
                <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-prestigeGold text-deepBlue shadow-glow">You</div>
            `;

        wrapper.querySelector('.livia-citation-trigger')?.addEventListener('click', () => {
            openCitationPopover(citations);
        });

        liviaThread.appendChild(wrapper);
        liviaScroll.scrollTop = liviaScroll.scrollHeight;
    };

    const saveThread = () => {
        const messages = Array.from(liviaThread.querySelectorAll('article')).slice(1).map((node) => {
            return {
                role: node.dataset.role || 'assistant',
                content: node.dataset.content || '',
                meta: node.dataset.meta || '',
                citations: JSON.parse(node.dataset.citations || '[]'),
            };
        }).map(normalizeThreadMessage).filter(Boolean);
        localStorage.setItem(storageKey, JSON.stringify(messages));
    };

    const loadThread = () => {
        const raw = localStorage.getItem(storageKey);
        if (!raw) return;
        try {
            const parsed = JSON.parse(raw);
            const messages = Array.isArray(parsed) ? parsed : [];
            const normalizedMessages = messages.map(normalizeThreadMessage).filter(Boolean);

            if (!normalizedMessages.length) {
                localStorage.removeItem(storageKey);
                return;
            }

            normalizedMessages.forEach((message) => renderMessage(message));
            localStorage.setItem(storageKey, JSON.stringify(normalizedMessages));
        } catch {
            localStorage.removeItem(storageKey);
        }
    };

    const sendPrompt = async (prompt) => {
        renderMessage({ role: 'user', content: prompt, meta: '' });
        liviaStatus.textContent = 'Livia sedang menyiapkan jawaban...';
        liviaProviderBadge.textContent = 'Processing';
        liviaSend.disabled = true;
        liviaSend.classList.add('opacity-70', 'cursor-not-allowed');

        const response = await fetch('/livia/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const payload = await response.json();

        if (!response.ok) {
            renderMessage({ role: 'assistant', content: payload.error || 'Terjadi kegagalan saat memanggil Livia.', meta: 'Error response', citations: [] });
            liviaStatus.textContent = 'Terjadi kendala. Silakan ulangi pertanyaan.';
            liviaProviderBadge.textContent = 'Error';
            liviaSend.disabled = false;
            liviaSend.classList.remove('opacity-70', 'cursor-not-allowed');
            saveThread();
            return;
        }

        renderMessage({
            role: 'assistant',
            content: payload.reply,
            meta: payload.provider_status || payload.provider || 'Completed',
            citations: payload.citations || [],
        });
        liviaProviderBadge.textContent = payload.provider || 'Completed';
        liviaStatus.textContent = 'Jawaban selesai dibuat.';
        liviaSend.disabled = false;
        liviaSend.classList.remove('opacity-70', 'cursor-not-allowed');
        saveThread();
    };

    liviaSend?.addEventListener('click', async () => {
        const prompt = liviaInput.value.trim();
        if (!prompt) {
            liviaInput.focus();
            return;
        }
        liviaInput.value = '';
        await sendPrompt(prompt);
    });

    liviaInput?.addEventListener('keydown', async (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            liviaSend?.click();
        }
    });

    document.querySelectorAll('.livia-starter').forEach((button) => {
        button.addEventListener('click', () => {
            liviaInput.value = button.dataset.prompt || '';
            liviaInput.focus();
        });
    });

    liviaClear?.addEventListener('click', () => {
        const nodes = Array.from(liviaThread.querySelectorAll('article')).slice(1);
        nodes.forEach((node) => node.remove());
        localStorage.removeItem(storageKey);
        liviaStatus.textContent = 'Percakapan baru dimulai.';
        liviaProviderBadge.textContent = 'Ready';
    });

    liviaCitationBackdrop?.addEventListener('click', closeCitationPopover);
    liviaCitationClose?.addEventListener('click', closeCitationPopover);
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeCitationPopover();
        }
    });

    loadThread();
}
