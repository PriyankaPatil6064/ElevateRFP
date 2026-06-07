# ElevateRFP – Smart RFP Generation System

Rule-Based Multi-Agent Architecture for the Elevator Industry.

## Architecture

```
PDF Upload → Sales Agent (extract text)
           → Extraction Agent (regex: floors, capacity, speed)
           → Matching Agent (rule-based product selection)
           → Pricing Agent (base + install + logistics + margin)
           → Response Agent (template-based proposal)
           ← Orchestrator (controls full pipeline)
```

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# Runs on http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install   # skip if already done
npm start
# Runs on http://localhost:3000
```

## API Endpoints

| Method | Route       | Description                        |
|--------|-------------|------------------------------------|
| GET    | /           | Health check                       |
| POST   | /process    | Upload PDF → full pipeline result  |
| POST   | /download   | Upload PDF → download .txt proposal|

## Product Catalog

| ID      | Model            | Capacity | Max Floors | Speed  | Base Price |
|---------|------------------|----------|------------|--------|------------|
| ELV-100 | ElevateBasic 100 | 630 kg   | 10         | 1.0 m/s| $25,000   |
| ELV-200 | ElevateMid 200   | 1000 kg  | 20         | 1.6 m/s| $45,000   |
| ELV-300 | ElevateHigh 300  | 1600 kg  | 40         | 2.5 m/s| $75,000   |
| ELV-400 | ElevateSuper 400 | 2000 kg  | 60         | 4.0 m/s| $120,000  |
| ELV-500 | ElevateUltra 500 | 3000 kg  | 100        | 6.0 m/s| $200,000  |

## Pricing Formula
```
Total = (Base Price + Floors × $800 + $5,000 logistics) × 1.15 margin
```
