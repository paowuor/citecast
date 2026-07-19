# 🎬 CiteCast - Citation-Aware Document to Multimedia Generator

[![Backblaze B2](https://img.shields.io/badge/Backblaze-B2-blue)](https://www.backblaze.com/b2/cloud-storage.html)
[![Genblaze](https://img.shields.io/badge/Genblaze-SDK-green)](https://github.com/backblaze/genblaze)
[![GMI Cloud](https://img.shields.io/badge/GMI-Cloud-orange)](https://gmi.cloud)
[![Hackathon](https://img.shields.io/badge/Backblaze-GenAI%20Hackathon-purple)](https://devpost.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Turn any document into an AI-generated video with clickable citations that link back to the original source.**

> 🏆 Built for the [Backblaze Generative Media Hackathon](https://devpost.com)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Why CiteCast?](#-why-citecast)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Hackathon Submission](#-hackathon-submission)
- [License](#-license)
- [Acknowledgements](#-acknowledgements)

---

## 🌟 Overview

**CiteCast** is an AI-powered application that transforms any PDF document into a multimedia presentation with **verifiable citations**. Every claim in the generated video links back to specific source text chunks, making it perfect for enterprise, education, and compliance-focused use cases.

### The Problem We Solve

- ❌ **AI Hallucinations**: Generated content often makes things up
- ❌ **No Audit Trail**: Can't verify where information came from
- ❌ **One-Size-Fits-All**: Same output for every audience
- ❌ **Disconnected Content**: Media assets with no source context

### Our Solution

- ✅ **Citation-Aware Generation**: Every claim is backed by source text
- ✅ **Clickable Citations**: View the exact source paragraph
- ✅ **Audience-Adaptive**: Executive, Engineer, or Student versions
- ✅ **Complete Audit Trail**: Export citations for compliance

---

## ✨ Key Features

### 1. 📄 Document Processing
- Upload any PDF document
- Automatic text extraction with page position tracking
- Intelligent chunking for optimal RAG performance
- Embedding generation for semantic search

### 2. 🎯 Audience-Aware Summarization
Generate different summaries based on audience:
| Audience | Focus | Output Style |
|----------|-------|--------------|
| **Executive** | Strategic insights, key metrics, business impact | Concise, high-level, actionable |
| **Engineer** | Technical specs, architecture, implementation | Detailed, precise, technical |
| **Student** | Core concepts, simple explanations | Accessible, educational, engaging |

### 3. 🔗 Citation Generation (RAG)
- Each claim is mapped to source chunks using semantic similarity
- Confidence scores (High/Medium/Low) for trust assessment
- Page numbers and character positions for precise referencing
- Context preservation with surrounding text

### 4. 🎨 AI Media Generation
- **Images**: GMI Cloud Seedream / Google Imagen
- **Audio**: ElevenLabs / Stability Audio
- **Video**: Scene compilation with synchronized audio
- **Parallel Generation**: Multiple assets generated simultaneously

### 5. 🖱️ Interactive Player
- Clickable scene markers for navigation
- Citation sidebar showing source text
- Confidence indicators (color-coded)
- Export citations as JSON or CSV

### 6. ☁️ Durable Storage with Backblaze B2
- All generated assets stored in B2
- Complete provenance manifests
- Hierarchical organization by job and audience
- S3-compatible API for easy integration

---

## 🎯 Why CiteCast?

### Compared to Other Solutions

| Feature | CiteCast | ChatGPT | Traditional Video Tools |
|---------|----------|---------|------------------------|
| Source Citations | ✅ Clickable | ❌ Not linked | ❌ None |
| Audience Adaptation | ✅ 3 modes | ⚠️ Basic prompt | ❌ One format |
| Audit Trail | ✅ Full manifest | ❌ None | ❌ None |
| Document Processing | ✅ RAG-based | ⚠️ Prompt only | ❌ N/A |
| AI Media Generation | ✅ Multiple providers | ⚠️ Limited | ❌ None |
| Enterprise Ready | ✅ Production-minded | ❌ No | ⚠️ Manual |

### Unique Value Proposition

> **"Trustworthy AI media with verifiable sources"**

CiteCast is the **only** solution that:
1. Generates AI media **and** provides clickable citations
2. Adapts content for different audiences **automatically**
3. Creates a complete **audit trail** for compliance
4. Stores everything in **durable, S3-compatible** storage

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER UPLOADS PDF                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT PROCESSOR                              │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  • Parse PDF (pdfplumber / pypdf)                         │   │
│  │  • Extract text with page/position tracking               │   │
│  │  • Chunk text (512 tokens, 50 overlap)                    │   │
│  │  • Generate embeddings (sentence-transformers)            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  • Store processed document in B2                         │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GENBLAZE PIPELINE                              │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Step 1: Audience-Aware Summarization                     │   │
│  │  └── LLM (GMI Cloud Llama 3 / OpenAI GPT-4)              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Step 2: Citation Generation (RAG)                        │   │
│  │  └── Semantic similarity search                          │   │
│  │  └── Confidence scoring (0.0 - 1.0)                      │   │
│  │  └── Page/position tracking                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Step 3: Parallel Media Generation (Fan-out)              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │  │   Images    │  │   Audio     │  │   Video     │      │   │
│  │  │   (GMI/     │  │  (ElevenLabs│  │  (Runway/   │      │   │
│  │  │   Imagen)   │  │   /Stab)    │  │   Decart)   │      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKBLAZE B2 STORAGE                            │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  📁 bucket: citecast-assets                               │   │
│  │  ├── 📁 raw-documents/                                    │   │
│  │  │   └── original.pdf                                    │   │
│  │  ├── 📁 processed-documents/                              │   │
│  │  │   └── {job_id}/processed.json  (chunks + embeddings)  │   │
│  │  └── 📁 generated-assets/                                 │   │
│  │      └── 📁 {job_id}/                                     │   │
│  │          ├── 📁 executive/                                │   │
│  │          │   ├── 📁 scenes/ (scene_1.png, ...)          │   │
│  │          │   ├── 📁 audio/ (scene_1.mp3, ...)           │   │
│  │          │   └── 📄 manifest.json  ← Citation Map        │   │
│  │          ├── 📁 engineer/                                 │   │
│  │          └── 📁 student/                                  │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    WEB FRONTEND (FastAPI + Jinja2)                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  • Upload interface (drag-and-drop)                       │   │
│  │  • Interactive video player with scene markers            │   │
│  │  • Citation sidebar (click to see source)                 │   │
│  │  • Export citations (JSON / CSV)                          │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Orchestration** | Genblaze SDK | AI workflow orchestration |
| **Storage** | Backblaze B2 | S3-compatible cloud storage |
| **Text Models** | GMI Cloud Llama 3, OpenAI GPT-4 | Summarization & reasoning |
| **Image Models** | GMI Cloud Seedream, Google Imagen | Image generation |
| **Audio Models** | ElevenLabs, Stability Audio | Voice generation |
| **Embeddings** | sentence-transformers | RAG & semantic search |
| **Document Processing** | LangChain, pdfplumber, pypdf | PDF parsing & chunking |
| **Web Framework** | FastAPI | Backend API |
| **Frontend** | HTML5, CSS3, Vanilla JS | User interface |
| **Templating** | Jinja2 | Server-side rendering |
| **Testing** | pytest | Unit testing |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Backblaze B2 Account ([Sign up for free](https://www.backblaze.com/b2/cloud-storage.html))
- GMI Cloud Account ([Request hackathon credits](https://gmi.cloud))
- OpenAI API Key (optional, for fallback)

### One-Line Setup (Linux/macOS)

```bash
git clone https://github.com/yourusername/citecast.git && cd citecast && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env
```

### One-Line Setup (Windows)

```cmd
git clone https://github.com/yourusername/citecast.git && cd citecast && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && copy .env.example .env
```

---

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/citecast.git
cd citecast
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual API keys:

```env
# Backblaze B2 (Required)
B2_KEY_ID=your_key_id_here
B2_APP_KEY=your_app_key_here
B2_BUCKET_NAME=citecast-assets

# GMI Cloud (Primary - Get hackathon credits!)
GMI_API_KEY=your_gmi_api_key_here

# OpenAI (Fallback - Optional)
OPENAI_API_KEY=your_openai_key_here

# Google Gemini (Fallback - Optional)
GEMINI_API_KEY=your_gemini_key_here

# Application Settings
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### Step 5: Create Required Directories

```bash
mkdir -p test_data uploads generated_assets processed_data citation_output
```

### Step 6: Run the Application

```bash
python scripts/run_web_server.py
```

Visit `http://localhost:8000` to use the application.

---

## 📖 Usage Guide

### 1. Upload a Document

1. Navigate to the homepage
2. Click "Browse" or drag-and-drop a PDF
3. Select target audience:
   - **Executive**: High-level strategic summary
   - **Engineer**: Technical deep dive
   - **Student**: Simplified overview
4. Choose number of scenes (3-10)
5. Click "Generate Media"

> ⏱️ Processing typically takes 1-3 minutes depending on document size and number of scenes.

### 2. View Generated Media

1. Click "View Result" when processing completes
2. Navigate through scenes using:
   - **Clicking** scene markers below the video
   - **Arrow keys** (←/→) on your keyboard
   - **Prev/Next** buttons

### 3. Explore Citations

1. Click on any scene or scene marker
2. The sidebar will display:
   - **Claim text** (the generated statement)
   - **Source citations** with page numbers
   - **Confidence levels** (High/Medium/Low)
   - **Text previews** of source chunks
   - **Section titles** (if available)

### 4. Export Citations

Click the export buttons to download:
- **📄 Export JSON**: Full manifest with all metadata
- **📊 Export CSV**: Flat table of all citations

### 5. Example Workflow

```
1. Upload "Annual_Report_2025.pdf"
2. Select "Executive" audience
3. Generate 5 scenes
4. View result → Click scene 2
5. See citation: "Page 7, 'Revenue grew 32% in Q4'"
6. Export citations for audit committee
```

---

## 🔌 API Reference

### GET `/`
Serve the main upload page.

### GET `/viewer/{job_id}`
Serve the media viewer for a specific job.

### POST `/api/jobs`
Create a new pipeline job.

**Parameters**:
- `file`: PDF file (multipart/form-data)
- `audience`: `executive` | `engineer` | `student`
- `num_scenes`: Integer (1-10)

**Response**:
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "processing",
  "viewer_url": "/viewer/job_a1b2c3d4",
  "message": "Job created and processing started"
}
```

### GET `/api/jobs/{job_id}`
Get job status.

**Response**:
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "completed",
  "audience": "executive",
  "created_at": "2026-07-19T10:30:00Z",
  "updated_at": "2026-07-19T10:35:00Z",
  "output_path": "generated-assets/job_a1b2c3d4/executive/",
  "manifest_path": "generated-assets/job_a1b2c3d4/executive/manifest.json"
}
```

### GET `/api/jobs/{job_id}/scenes`
Get all scenes with citations.

**Response**:
```json
{
  "job_id": "job_a1b2c3d4",
  "total_scenes": 5,
  "scenes": [
    {
      "scene_id": "scene_000",
      "order": 0,
      "claim_text": "Revenue grew 32% in Q4 2024",
      "image_url": "/generated/job_a1b2c3d4/executive/scenes/scene_000.png",
      "audio_url": "/generated/job_a1b2c3d4/executive/audio/scene_000.mp3",
      "citations": [
        {
          "chunk_id": "chunk_0000",
          "text_preview": "Revenue grew 32% in Q4 2024, driven by new product launches...",
          "page": 7,
          "confidence_level": "high",
          "similarity_score": 0.92
        }
      ],
      "timestamp_start": 0.0,
      "timestamp_end": 3.0
    }
  ]
}
```

### GET `/api/jobs/{job_id}/citations/export`
Export citations.

**Parameters**:
- `format`: `json` | `csv`

**Response (JSON)**: Full manifest
**Response (CSV)**: Flat table of citations

### GET `/api/health`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-07-19T10:30:00Z",
  "b2_configured": true
}
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/
```

### Component Tests

```bash
# Test document processing
python scripts/test_document_processor.py

# Test citation generation
python scripts/test_citation_manager.py

# Test full pipeline
python scripts/test_pipeline.py
```

### Sample Test Output

```
📄 Processing: test_data/sample.pdf
📊 Processing Results:
  - Filename: sample.pdf
  - Pages: 12
  - Chunks: 18
  - Characters: 8756

📑 Sample Chunks:
  Chunk 1 (Page 1):
  ID: chunk_0000
  Text: Annual Report 2025...
  Section: Annual Report 2025
  Embedding dims: 384

🔍 Generating citations...
📊 Citation Results:
  - Total Claims: 5
  - Total Citations: 12
  - Confidence Distribution: {'high': 5, 'medium': 5, 'low': 2}
  - Coverage: 100.0%

✅ Pipeline completed in 45.23s
  Total Scenes: 5
  Total Citations: 12
  Manifest URL: s3://citecast-assets/generated-assets/job_abc123/executive/manifest.json
```

---

## 📁 Project Structure

```
citecast/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── document_processor.py    # PDF parsing & chunking
│   │   ├── citation_manager.py      # RAG & citation generation
│   │   ├── pipeline.py              # Genblaze orchestration
│   │   └── manifest_builder.py      # Citation manifest creation
│   ├── storage/
│   │   ├── __init__.py
│   │   └── b2_client.py             # Backblaze B2 integration
│   ├── web/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI server
│   │   └── static/
│   │       ├── index.html
│   │       ├── style.css
│   │       ├── script.js
│   │       └── player.js
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py                # Configuration management
│   │   ├── logging.py               # Logging setup
│   │   └── genblaze_config.py       # Genblaze provider config
│   └── __init__.py
├── scripts/
│   ├── run_web_server.py
│   ├── test_document_processor.py
│   ├── test_citation_manager.py
│   └── test_pipeline.py
├── templates/
│   ├── base.html
│   ├── index.html
│   └── viewer.html
├── tests/
│   ├── __init__.py
│   ├── test_document_processor.py
│   ├── test_citation_manager.py
│   └── test_pipeline.py
├── test_data/                      # Sample documents
├── uploads/                        # Uploaded files
├── generated_assets/               # Generated media
├── processed_data/                 # Processed documents
├── citation_output/                # Citation manifests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| **B2 Connection Failed** | Invalid credentials | Check `B2_KEY_ID` and `B2_APP_KEY` in `.env` |
| **GMI Cloud Error** | Missing/invalid API key | Request hackathon credits via form |
| **No Embeddings Generated** | Missing `sentence-transformers` | `pip install sentence-transformers` |
| **Slow Processing** | Large document or network latency | Reduce `num_scenes` or use smaller PDF |
| **Memory Error** | Document too large | Use PDF with <50 pages initially |
| **Missing FFmpeg** | Video assembly disabled | Install FFmpeg (optional) |
| **Port Already in Use** | Another server running | Change `PORT` in `.env` |

### Quick Fixes

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Clear cache
rm -rf __pycache__ .pytest_cache

# Reset environment
cp .env.example .env
# Re-enter your API keys

# Check B2 connection
python scripts/test_connection.py
```

### Getting Help

1. **Open an Issue**: [GitHub Issues](https://github.com/yourusername/citecast/issues)
2. **Genblaze Docs**: [Genblaze GitHub](https://github.com/backblaze/genblaze)
3. **Backblaze Community**: [Backblaze Discord](https://discord.gg/backblaze)
4. **GMI Cloud Support**: [GMI Cloud Docs](https://gmi.cloud/docs)

---

## 🏆 Hackathon Submission

### Requirements Checklist

- [x] **Working App**: Functional at `http://localhost:8000`
- [x] **GitHub Repo**: Public repository with setup instructions
- [x] **Providers & Models**: GMI Cloud, OpenAI, Google Gemini
- [x] **B2 & Genblaze Usage**: Document storage, media storage, pipeline orchestration
- [x] **Demo Video**: 3-minute walkthrough (to be recorded)

### Demo Video Outline

1. **Introduction (0:00-0:30)**
   - Show the problem: AI hallucinations and lack of citations
   - Introduce CiteCast as the solution

2. **Upload & Generate (0:30-1:30)**
   - Upload a sample PDF
   - Select audience (Executive/Engineer/Student)
   - Show processing progress
   - View the generated media

3. **Citation Feature (1:30-2:30)**
   - Click on a scene
   - Show the sidebar with citations
   - Click a citation to see source text
   - Demonstrate confidence levels

4. **Export & Compliance (2:30-3:00)**
   - Export citations as JSON
   - Export as CSV
   - Show the manifest structure

### Submission Links

- **Demo Video**: [YouTube Link]
- **GitHub Repository**: [https://github.com/yourusername/citecast](https://github.com/yourusername/citecast)
- **Live Demo**: [Deployed URL]
- **Devpost Submission**: [Hackathon Link]

---

## 📄 License

MIT License

Copyright (c) 2026 CiteCast Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 🙏 Acknowledgements

### Technology Partners

| Partner | Role |
|---------|------|
| **[Backblaze B2](https://www.backblaze.com/b2/)** | Cloud storage for all assets and manifests |
| **[Genblaze](https://github.com/backblaze/genblaze)** | Orchestration framework for AI workflows |
| **[GMI Cloud](https://gmi.cloud)** | Hosting for open source AI models |
| **[OpenAI](https://openai.com)** | Fallback LLM provider |
| **[Google Cloud](https://cloud.google.com)** | Gemini and Imagen models |
| **[ElevenLabs](https://elevenlabs.io)** | Voice synthesis |

### Open Source Libraries

- **LangChain**: Document processing and chunking
- **sentence-transformers**: Embedding generation
- **FastAPI**: Web framework
- **pdfplumber**: PDF parsing
- **pypdf**: PDF parsing (fallback)
- **pytest**: Testing framework
- **Jinja2**: Templating engine

### Team & Contributors

- [Paul Owuor] - Lead Developer
- [Paul Owuor] - Design & Frontend
- [Paul Owuor] - Documentation & Testing

---

## 📬 Contact & Support

- **GitHub**: [github.com/paowuor/citecast](https://github.com/paowuor/citecast)
- **Email**: owuorpaul500@gmail.com
- **LinkedIn**: [Your Profile](https://linkedin.com/in/yourprofile)

---

## ⭐ Star Us!

If you find CiteCast useful, please **star** the repository on GitHub!

[![GitHub Stars](https://img.shields.io/github/stars/paowuor/citecast?style=social)](https://github.com/paowuor/citecast)

---

**Built with ❤️ for the Backblaze Generative Media Hackathon**

<div align="center">
  <sub>🚀 2026 • Backblaze Generative Media Hackathon</sub>
</div>

---