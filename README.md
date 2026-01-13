# Insurance Agent Strands

Local agentic AI application for insurance claim validation using **AWS Strands SDK** with native human-in-the-loop support via interrupts.

## ✨ Features

- **🤖 AWS Strands Integration**: Official `strands-agents` SDK with LiteLLM + Gemini 2.0 Flash Lite
- **⏸️ Native Interrupts**: Human-in-the-loop approval flow using Strands interrupt system
- **💬 Session Management**: Automatic conversation history per claim via `FileSessionManager`
- **📊 Complete Audit Trail**: Messages, decisions, and agent interactions logged
- **🎨 Premium UI**: Glassmorphism design with AI summary display and risk badges
- **🔒 Role-Based Access**: USER, APPROVER, ADMIN roles with state-based authorization

## 🏗️ Architecture

- **Backend**: FastAPI, SQLite (FSM), Redis (optional), AWS Strands SDK
- **Frontend**: React 18, TypeScript, Vite, Vanilla CSS (A2UI principles)
- **Agent**: Strands Agent with interrupts, tools, and session management
- **Database**: SQLite with audit tables (messages, decisions, agent_audit)

## 🚀 Quick Start

### 1. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 2. Initialize Database

```bash
cd backend
python app/db/init_db.py
```

### 3. Start Services

**Backend (Terminal 1):**
```bash
cd backend
python -m uvicorn main:app --reload
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm run dev
```

### 4. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🔐 Test Credentials

### 👤 Users (Submit Claims)
| Username | Password | Role |
|----------|----------|------|
| `user` | `password` | USER |
| `john_user` | `password123` | USER |
| `sarah_user` | `password123` | USER |
| `mike_user` | `password123` | USER |

### ✅ Approvers (Review Claims)
| Username | Password | Role |
|----------|----------|------|
| `approver` | `password` | APPROVER |
| `emma_approver` | `password123` | APPROVER |
| `david_approver` | `password123` | APPROVER |

### 🔧 Admin (Full Access)
| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | ADMIN |

## 🧪 Testing the Interrupt Flow

### Test 1: Low-Risk Auto-Approval
1. Login as `user` / `password`
2. Submit claim with amount < $50,000
3. **Expected**: Claim auto-approved by agent (no interrupt)

### Test 2: High-Risk Interrupt Flow
1. Login as `user` / `password`
2. Submit claim with amount > $100,000
3. **Expected**: Agent raises interrupt → PENDING_APPROVAL
4. Logout, login as `approver` / `password`
5. See AI summary and risk badge
6. Approve/Reject/Request More Info

## 📊 How It Works

### Claim Submission Flow
```
1. User submits claim → DRAFT
2. User clicks "Submit" → UNDER_AGENT_REVIEW
3. Strands agent processes:
   - Validates completeness
   - Assesses risk (LOW/MEDIUM/HIGH)
   - For HIGH/MEDIUM: raises interrupt
4. Agent pauses → PENDING_APPROVAL
5. Approver reviews with AI summary
6. Approver decides:
   - Approve → APPROVED
   - Reject → REJECTED
   - Request Info → NEEDS_MORE_INFO
```

### Interrupt System (Human-in-the-Loop)
- Agent uses `request_approval` tool
- `ClaimApprovalHook` intercepts tool call
- Raises Strands interrupt (pauses execution)
- Stores interrupt ID in `claim_metadata`
- Frontend displays AI summary + risk level
- Approver responds via API
- Agent resumes with response

## 🛠️ Tech Stack Details

### Backend
- **Framework**: FastAPI (async)
- **Database**: SQLite + SQLAlchemy (async)
- **Agent**: AWS Strands SDK (`strands-agents[litellm]`)
- **LLM**: Gemini 2.0 Flash Lite via LiteLLM
- **Auth**: JWT with passlib
- **Cache**: Redis (optional, for locks/pub-sub)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Styling**: Vanilla CSS with glassmorphism
- **State**: React Context API
- **Routing**: React Router v6

### Agent Tools
1. `validate_claim()` - Check completeness
2. `assess_risk()` - Calculate risk level
3. `request_approval()` - Raise interrupt for human approval
4. `request_more_info()` - Generate clarification questions

## 📁 Project Structure

```
insurant_agent_strands/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── strands_service.py  # Strands agent implementation
│   │   │   └── tools.py            # Legacy tools
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       ├── auth.py         # JWT authentication
│   │   │       └── claims.py       # Claim endpoints
│   │   ├── models/
│   │   │   ├── user.py             # User model
│   │   │   ├── claim.py            # Claim model
│   │   │   └── audit.py            # Message, Decision, AgentAudit
│   │   ├── services/
│   │   │   └── claim_service.py    # Business logic
│   │   └── db/
│   │       └── init_db.py          # Database initialization
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx           # Login page
│   │   │   ├── Dashboard.tsx       # Approver dashboard
│   │   │   └── ClaimSubmit.tsx     # Claim submission
│   │   ├── context/
│   │   │   └── AuthContext.tsx     # Auth state
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## 🔍 Database Schema

### Core Tables
- `users` - User accounts with roles
- `claims` - Insurance claims with FSM states
- `messages` - Conversation history
- `decisions` - Approval/rejection audit trail
- `agent_audit` - LLM interaction logs

### Claim States (FSM)
- `DRAFT` → `UNDER_AGENT_REVIEW`
- `UNDER_AGENT_REVIEW` → `PENDING_APPROVAL`
- `PENDING_APPROVAL` → `APPROVED` | `REJECTED` | `NEEDS_MORE_INFO`
- `NEEDS_MORE_INFO` → `PENDING_APPROVAL`

## 🎯 Key Features

### AWS Strands Integration
- ✅ Official `strands-agents[litellm]` SDK
- ✅ Native interrupt system for human-in-the-loop
- ✅ Session management with `FileSessionManager`
- ✅ Tool decorators (`@tool`)
- ✅ Hook system (`ClaimApprovalHook`)
- ✅ Automatic conversation history

### Frontend UI
- ✅ AI agent summary display
- ✅ Risk level badges (HIGH/MEDIUM/LOW)
- ✅ 3-button approval flow
- ✅ Modal dialogs for reject/request-info
- ✅ Detailed submission feedback
- ✅ Glassmorphism design

### Security & Compliance
- ✅ JWT authentication
- ✅ Role-based authorization
- ✅ State-based access control
- ✅ Complete audit trail
- ✅ Replayable decisions

## 📚 Documentation

- **Migration Walkthrough**: See `.gemini/antigravity/brain/.../migration_walkthrough.md`
- **Test Credentials**: See `.gemini/antigravity/brain/.../test_credentials.md`
- **Implementation Review**: See `.gemini/antigravity/brain/.../implementation_review.md`
- **Strands Compliance**: See `.gemini/antigravity/brain/.../strands_compliance_addendum.md`

## 🐛 Troubleshooting

### Database Issues
```bash
# Reinitialize database
cd backend
python app/db/init_db.py
```

### Login Not Working
```bash
# Create test users
python create_users.py
```

### Agent Sessions
- Sessions stored in `./agent_sessions/claim-{id}/`
- Each claim gets unique session for conversation history

## 📝 License

MIT

## 🤝 Contributing

This is a demonstration project for AWS Strands integration patterns.
