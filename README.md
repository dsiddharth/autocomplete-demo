# LLM Autocomplete Demo

A local demo of LLM-driven autocomplete using Qwen2-0.5B model.

## Features

- Real-time code autocomplete using a local LLM
- Low-latency inference
- Multiple suggestion options
- Keyboard navigation
- Modern UI with CodeMirror editor

## Setup

### Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Start the backend server:
```bash
python app.py
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

## Architecture

- Backend: FastAPI server with Qwen2-0.5B model
- Frontend: React with CodeMirror editor
- Model: Qwen2-0.5B quantized for fast inference

## License

MIT 