# ADHuman-extension

ADHuman is a hybrid Human-in-the-loop architecture designed to improve human judgment directly into the decision-making adaptation process, particularly in the Analyse phase of the MAPE-K model.

The system implements a **Human-AI collaborative mitigation model**, where automatic accessibility fixes are applied first and manual adjustments are enabled if necessary.

---

# Overview

Many websites fail to satisfy the **minimum color contrast requirements** defined in WCAG.

ADHuman addresses this problem using a **two-stage mitigation process**:

| Stage   | Mode              | Trigger                       | Behavior                                             |
| ------- | ----------------- | ----------------------------- | ---------------------------------------------------- |
| Stage 0 | Automatic         | 5 seconds after page load     | Automatically adjusts text color to improve contrast |
| Stage 1 | Human-in-the-loop | 10 seconds of user inactivity | Enables manual adjustments on flagged elements       |

The system visually highlights problematic elements and provides a small UI to guide users in applying corrections.

---

# Architecture

The agent runs as a **Chrome Extension (Manifest V3)**.

```
Browser Page
     │
     ▼
Content Script
     │
     ▼
ADHumanWCAG Agent
     │
     ├── Contrast Detection
     ├── Automatic Mitigation (Stage 0)
     └── Manual Adjustment (Stage 1)
```

---

# Repository Structure

```
adhuman-wcag-143
│
├── extension
│   ├── manifest.json
│   ├── adhuman-core.js
│   └── content.js
│
├── docs
│   └── architecture.md
│
└── README.md
```

### extension/

Contains the Chrome extension implementation.

* `manifest.json` — extension configuration
* `adhuman-core.js` — main accessibility mitigation agent
* `content.js` — initialization script

---

# How It Works

### 1. Contrast Detection

The agent scans the DOM and computes the **contrast ratio** between text and background colors using the WCAG luminance formula.

Thresholds used:

* **Normal text:** contrast ≥ 4.5:1
* **Large text:** contrast ≥ 3.0:1

If a violation is detected, the element is flagged visually.

---

### 2. Automatic Mitigation (Stage 0)

After **5 seconds**, the system:

1. Detects contrast failures
2. Selects the best contrast text color (black or white)
3. Applies automatic mitigation

Users are notified via a small toast notification.

---

### 3. Manual Mitigation (Stage 1)

If the user remains inactive for **10 seconds**, the system enables **manual interaction**.

Users can click flagged elements and choose:

* Automatic text correction
* Black/white contrast pair
* Revert modification

This enables **human supervision over automated accessibility repair**.

---

# Installation

### 1. Clone the repository

```
git clone https://github.com/YOUR_USERNAME/adhuman-wcag-143
```

### 2. Open Chrome Extensions

```
chrome://extensions
```

### 3. Enable Developer Mode

Toggle **Developer Mode** in the top right.

### 4. Load the extension

Click **Load unpacked** and select the `extension` folder.

---

# WCAG Target

This agent mitigates violations of:

**WCAG 2.1 Success Criterion 1.4.3**

Contrast (Minimum)

Official specification:

https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html

---

# Research Motivation

ADHuman demonstrates a **timed human-AI collaboration model** for accessibility mitigation.

Instead of relying solely on automated fixes, the system:

* first attempts automatic mitigation
* then invites human intervention
* preserves reversibility of changes

This approach aims to support **accessible web experiences without disrupting original page design**.

---

# Future Work

Possible extensions include:

* additional WCAG criteria mitigation
* machine-learning-based color adaptation
* browser-independent implementation
* user preference learning

---

# License

MIT License
