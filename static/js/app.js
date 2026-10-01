(() => {
  const form = document.querySelector("#complaint-form");
  const complaintInput = document.querySelector("#complaint-text");
  const languageInput = document.querySelector("#language");
  const formMessage = document.querySelector("#form-message");
  const characterCount = document.querySelector("#character-count");
  const speakButton = document.querySelector("#speak-button");
  const voiceStatus = document.querySelector("#voice-status");

  if (form && complaintInput && languageInput) {
    const submitButton = document.querySelector("#submit-button");
    const updateCharacterCount = () => {
      characterCount.textContent = `${complaintInput.value.length.toLocaleString()} / 5,000`;
    };
    complaintInput.addEventListener("input", updateCharacterCount);

    document.querySelectorAll("[data-example]").forEach((button) => {
      button.addEventListener("click", () => {
        complaintInput.value = button.dataset.example || "";
        updateCharacterCount();
        complaintInput.focus();
      });
    });

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    if (!SpeechRecognition) {
      speakButton.disabled = true;
      speakButton.title = "Speech recognition is not supported in this browser. Type your complaint instead.";
      voiceStatus.textContent = "Voice input is not supported here. You can type your complaint.";
    } else {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      speakButton.addEventListener("click", () => {
        recognition.lang = languageInput.value === "ta" ? "ta-IN" : "en-IN";
        voiceStatus.classList.remove("is-error");
        voiceStatus.classList.add("is-listening");
        voiceStatus.textContent = "Listening… speak now";
        speakButton.disabled = true;
        try {
          recognition.start();
        } catch (_error) {
          voiceStatus.classList.remove("is-listening");
          voiceStatus.classList.add("is-error");
          voiceStatus.textContent = "Voice input could not start. Please try again or type your complaint.";
          speakButton.disabled = false;
        }
      });
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join(" ")
          .trim();
        if (transcript) {
          complaintInput.value = [complaintInput.value.trim(), transcript].filter(Boolean).join(" ");
          updateCharacterCount();
          voiceStatus.textContent = "Transcription added. Review it before submitting.";
          complaintInput.focus();
        } else {
          voiceStatus.textContent = "No speech was detected. Try again or type your complaint.";
        }
      };
      recognition.onerror = (event) => {
        const messages = {
          "not-allowed": "Microphone permission was denied. Allow access or type your complaint.",
          "service-not-allowed": "Speech recognition is unavailable. You can type your complaint.",
          "no-speech": "No speech was detected. Try again in a quieter place.",
          "audio-capture": "No microphone was found. Check your device or type your complaint.",
          network: "Speech recognition needs a network connection in this browser.",
        };
        voiceStatus.classList.remove("is-listening");
        voiceStatus.classList.add("is-error");
        voiceStatus.textContent = messages[event.error] || "Voice input stopped. Please try again or type your complaint.";
      };
      recognition.onend = () => {
        speakButton.disabled = false;
        voiceStatus.classList.remove("is-listening");
        if (!voiceStatus.classList.contains("is-error") && voiceStatus.textContent === "Listening… speak now") {
          voiceStatus.textContent = "Voice input is ready";
        }
      };
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      formMessage.textContent = "";
      formMessage.classList.remove("is-error");
      if (!complaintInput.value.trim()) {
        formMessage.textContent = "Please enter a complaint before submitting.";
        formMessage.classList.add("is-error");
        complaintInput.focus();
        return;
      }
      submitButton.disabled = true;
      submitButton.innerHTML = 'Submitting… <span aria-hidden="true">·</span>';
      try {
        const response = await fetch("/api/complaints", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ complaint_text: complaintInput.value, language: languageInput.value }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "We could not submit your complaint.");
        complaintInput.value = "";
        updateCharacterCount();
        if (data.human_verification_required) {
          formMessage.textContent = "Your complaint was submitted. It received a critical assistive flag; an officer must verify the situation directly.";
        } else {
          formMessage.textContent = "Your complaint was submitted for officer review.";
        }
      } catch (error) {
        formMessage.textContent = error.message || "A connection error occurred. Please try again.";
        formMessage.classList.add("is-error");
      } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = 'Submit complaint <span aria-hidden="true">→</span>';
      }
    });
  }

  const complaintList = document.querySelector("#complaint-list");
  if (!complaintList) return;

  const queueMessage = document.querySelector("#queue-message");
  const priorityFilter = document.querySelector("#priority-filter");
  const criticalAlert = document.querySelector("#critical-alert");
  const knownCriticalIds = new Set();
  let firstLoad = true;
  let cachedComplaints = [];

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
  const formatTime = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Time unavailable";
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
  };
  const statusLabel = (status) => status.replaceAll("_", " ");
  const nextStatus = { NEW: ["ACKNOWLEDGED", "Acknowledge"], ACKNOWLEDGED: ["IN_PROGRESS", "Start work"], IN_PROGRESS: ["RESOLVED", "Resolve"] };

  const renderComplaint = (complaint, index) => {
    const priority = escapeHtml(complaint.priority);
    const factors = Array.isArray(complaint.detected_factors) ? complaint.detected_factors : [];
    const factorMarkup = factors.length
      ? factors.map((factor) => `<span class="factor-chip">${escapeHtml(factor.label || "Reported signal")}</span>`).join("")
      : '<span class="no-factors">No specific signals detected</span>';
    const step = nextStatus[complaint.status];
    const actionMarkup = step
      ? `<button class="status-action" data-action="status" data-id="${Number(complaint.id)}" data-status="${step[0]}">${step[1]}</button>`
      : "";
    return `<article class="complaint-card priority-${priority.toLowerCase()}" style="animation-delay:${Math.min(index * 35, 210)}ms">
      <div class="complaint-main">
        <div class="complaint-meta"><span class="priority-badge badge-${priority.toLowerCase()}">${priority}</span><span class="complaint-id">CASE #${Number(complaint.id)}</span><time class="complaint-time" datetime="${escapeHtml(complaint.created_at)}">${escapeHtml(formatTime(complaint.created_at))}</time></div>
        <p class="complaint-text">${escapeHtml(complaint.complaint_text)}</p>
        <div class="complaint-details"><div><span class="detail-label">DETECTED FACTORS</span><div class="factor-list">${factorMarkup}</div></div><div><span class="detail-label">AI-ASSISTED EXPLANATION · SCORE ${Number(complaint.score)}/100</span><p class="detail-copy">${escapeHtml(complaint.explanation)}</p></div></div>
      </div>
      <div class="complaint-side"><span class="status-pill status-${escapeHtml(complaint.status.toLowerCase())}">${escapeHtml(statusLabel(complaint.status))}</span>${actionMarkup}</div>
    </article>`;
  };

  const updateAlert = (complaints, notifyNew) => {
    const activeCritical = complaints.filter((complaint) => complaint.priority === "CRITICAL" && complaint.status !== "RESOLVED");
    if (activeCritical.length) {
      const latest = activeCritical[0];
      criticalAlert.hidden = false;
      document.querySelector("#critical-alert-title").textContent = `${activeCritical.length} critical report${activeCritical.length === 1 ? " needs" : "s need"} officer verification`;
      document.querySelector("#critical-alert-copy").textContent = `Latest: ${latest.complaint_text.slice(0, 150)}${latest.complaint_text.length > 150 ? "…" : ""}`;
    } else {
      criticalAlert.hidden = true;
    }
    for (const complaint of activeCritical) {
      if (notifyNew && !knownCriticalIds.has(complaint.id) && "Notification" in window && Notification.permission === "granted") {
        new Notification("🚨 CRITICAL COMPLAINT", {
          body: "An officer must verify this report. Open the dashboard to review.",
          tag: `complaint-${complaint.id}`,
        });
      }
      knownCriticalIds.add(complaint.id);
    }
  };

  const renderQueue = () => {
    const selectedPriority = priorityFilter.value;
    const visible = selectedPriority === "ALL"
      ? cachedComplaints
      : cachedComplaints.filter((complaint) => complaint.priority === selectedPriority);
    document.querySelector("#queue-count").textContent = visible.length;
    complaintList.innerHTML = visible.map(renderComplaint).join("");
    document.querySelector("#empty-state").hidden = visible.length !== 0;
    complaintList.hidden = visible.length === 0;
  };

  const refreshComplaints = async () => {
    try {
      const response = await fetch("/api/complaints", { headers: { Accept: "application/json" } });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "The queue could not be loaded.");
      cachedComplaints = data.complaints;
      document.querySelector("#stat-total").textContent = data.stats.total;
      document.querySelector("#stat-critical").textContent = data.stats.critical;
      document.querySelector("#stat-high").textContent = data.stats.high;
      document.querySelector("#stat-medium").textContent = data.stats.medium;
      document.querySelector("#stat-normal").textContent = data.stats.normal;
      document.querySelector("#sidebar-total").textContent = data.stats.total;
      updateAlert(cachedComplaints, !firstLoad);
      firstLoad = false;
      queueMessage.textContent = "";
      renderQueue();
    } catch (error) {
      complaintList.innerHTML = `<div class="loading-state">${escapeHtml(error.message || "The queue could not be loaded.")}</div>`;
      queueMessage.textContent = "Check your connection and try refreshing.";
      queueMessage.classList.add("is-error");
    }
  };

  const addDemoData = async () => {
    const buttons = [document.querySelector("#demo-button"), document.querySelector("#empty-demo-button")].filter(Boolean);
    buttons.forEach((button) => { button.disabled = true; });
    try {
      const response = await fetch("/api/demo-data", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Demo data could not be loaded.");
      queueMessage.classList.remove("is-error");
      queueMessage.textContent = "Demo complaints added. The critical medical-support report is ranked first.";
      await refreshComplaints();
    } catch (error) {
      queueMessage.classList.add("is-error");
      queueMessage.textContent = error.message || "Demo data could not be loaded.";
    } finally {
      buttons.forEach((button) => { button.disabled = false; });
    }
  };

  document.querySelector("#refresh-button").addEventListener("click", refreshComplaints);
  document.querySelector("#demo-button").addEventListener("click", addDemoData);
  document.querySelector("#empty-demo-button").addEventListener("click", addDemoData);
  priorityFilter.addEventListener("change", renderQueue);
  document.querySelector("#enable-alerts").addEventListener("click", async (event) => {
    if (!("Notification" in window)) {
      queueMessage.textContent = "Browser notifications are not supported here.";
      return;
    }
    const permission = await Notification.requestPermission();
    event.currentTarget.textContent = permission === "granted" ? "Alerts enabled" : "Alerts not enabled";
    queueMessage.textContent = permission === "granted"
      ? "Browser alerts are enabled for new critical reports."
      : "Browser notifications were not allowed. The on-screen critical alert remains active.";
  });
  complaintList.addEventListener("click", async (event) => {
    const button = event.target.closest('[data-action="status"]');
    if (!button) return;
    button.disabled = true;
    try {
      const response = await fetch(`/api/complaints/${button.dataset.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: button.dataset.status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Status could not be updated.");
      queueMessage.classList.remove("is-error");
      queueMessage.textContent = `Case #${data.complaint.id} marked ${statusLabel(data.complaint.status).toLowerCase()}.`;
      await refreshComplaints();
    } catch (error) {
      queueMessage.classList.add("is-error");
      queueMessage.textContent = error.message || "Status could not be updated.";
      button.disabled = false;
    }
  });

  refreshComplaints();
  window.setInterval(refreshComplaints, 15000);
})();
