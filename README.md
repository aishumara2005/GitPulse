# 🚀 GitPulse -- AI Powered GitHub Team Intelligence Platform

> **Monitor • Analyze • Secure • Improve**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_App-black?style=for-the-badge&logo=flask)
![GitHub
API](https://img.shields.io/badge/GitHub-API-success?style=for-the-badge&logo=github)
![AI](https://img.shields.io/badge/AI-Claude-orange?style=for-the-badge)

------------------------------------------------------------------------

## 📌 Project Overview

GitPulse is an AI-powered GitHub Team Intelligence Platform that helps
developers and organizations monitor repositories, analyze contributor
activity, scan code for security issues, and generate AI-powered
insights through an interactive dashboard.

## ✨ Features

-   🔐 GitHub OAuth Authentication
-   📊 Repository Analytics
-   👥 Contributor Insights
-   🤖 AI Recommendations
-   🛡️ Security & Secret Scanner
-   📈 Interactive Dashboard
-   📧 Email Notifications
-   📂 Multi-Repository Ready

## 🏗️ Workflow

``` text
GitHub Repository
        │
        ▼
 GitHub API
        │
        ▼
 Flask Backend
        │
 ┌──────┴────────┐
 ▼               ▼
AI Analysis  Security Scan
 └──────┬────────┘
        ▼
 Analytics Dashboard
        ▼
 Email Notifications
```

## 🖼️ Architecture

``` mermaid
flowchart LR
A[GitHub Repository]-->B[GitHub API]
B-->C[Flask Backend]
C-->D[AI Engine]
C-->E[Security Scanner]
D-->F[SQLite]
E-->F
F-->G[Dashboard]
G-->H[Notifications]
```

## 🛠️ Tech Stack

  Category   Technologies
  ---------- ----------------------------------
  Frontend   HTML, CSS, Bootstrap, JavaScript
  Backend    Python, Flask
  AI         Claude API
  APIs       GitHub REST API
  Database   SQLite

## 📂 Project Structure

``` text
GitPulse/
├── app.py
├── ai_analyzer.py
├── github_api.py
├── security_scanner.py
├── templates/
├── static/
├── requirements.txt
└── README.md
```

## ⚙️ Installation

``` bash
git clone https://github.com/aishumara2005/GitPulse.git
cd GitPulse
pip install -r requirements.txt
python app.py
```

## 👨‍💻 Contributors

  Name                  Role
  --------------------- --------------
  Aiswarya Maravarman   Project Lead
  Arun                  Contributor

## 📜 License

MIT License

## 📬 Contact

-   GitHub: https://github.com/aishumara2005
-    GitHub:https://github.com/Arun15226
-   LinkedIn: https://www.linkedin.com/in/aiswarya-maravarman-8a5550371/
-   LinkedIn:https://www.linkedin.com/in/kausik-arun-33626641b?utm_source=share_via&utm_content=profile&utm_medium=member_android
