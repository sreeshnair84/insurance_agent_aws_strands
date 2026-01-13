# Insurance Agent Strands

**AI-powered insurance claim processing system showcasing Human-in-the-Loop workflows, Agentic Automation, and Rich Chat (A2UI) interfaces.**

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green)

## Overview

Insurance Agent Strands is a modern demonstration of an intelligent agent system designed to streamline insurance claims. It leverages **Google Gemini** for reasoning and **AWS Strands** architectural principles to create a robust, transparent, and user-friendly experience.

The system features a **General Chat** interface where users can naturally interact with the AI to:
- List existing claims.
- Create new claim drafts via conversational forms.
- Inquiry about claim status and policy details.
- Clear chat history and manage sessions.

It employs **A2UI (Agent-to-UI)** technology to render structured components (Tables, Forms, Status Cards) directly within the chat stream, moving beyond simple text responses.

## Key Features

- **🤖 Intelligent Agent**: Built with `strands` and Google Gemini Pro, capable of using tools to query databases and perform actions.
- **💬 Rich Chat Interface**: Supports "General Chat" for broad inquiries and specific "Claim Context" chat.
- **📊 A2UI Integration**: The agent can dynamically generate UI components:
    - **Table Cards**: For listing claims or structured data.
    - **Form Cards**: For collecting user input (e.g., filing a claim).
    - **Status Cards**: Visual indicators for system status or errors (e.g., Rate Limits).
- **🛡️ Human-in-the-Loop**: Claims move through states (Draft -> AI Review -> Human Approval) ensuring oversight.
- **🗑️ Session Management**: Users can clear chat history to start fresh conversations.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (Async/Await via SQLAlchemy)
- **AI/LLM**: Google Gemini (via LiteLLM)
- **Agent Framework**: Custom `strands` implementation
- **Cache**: Redis (Optional)

### Frontend
- **Framework**: React (Vite)
- **Styling**: Vanilla CSS (Modern, Responsive)
- **State Management**: React Context API

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 16+
- Google Gemini API Key

### Backend Setup
1.  Navigate to `backend`:
    ```bash
    cd backend
    ```
2.  Create virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure Environment:
    - Create a `.env` file in `backend/` (see `.env.example` or use the snippet below).
    ```env
    PROJECT_NAME="Insurance Agent Strands"
    GEMINI_API_KEY="your_api_key_here"
    SECRET_KEY="your_secret_key"
    ```
5.  Run the server:
    ```bash
    python -m uvicorn main:app --reload
    ```

### Frontend Setup
1.  Navigate to `frontend`:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```

## Usage
1.  Open the frontend (default: `http://localhost:5173`).
2.  Login (Test User: `testuser` / `password`).
3.  Navigate to **Chat**.
4.  Try commands like:
    - "List my claims"
    - "Create a new claim for policy P-123"
    - "Clear chat"

## License
MIT
