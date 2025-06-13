# StruMind - Next-Generation Structural Engineering Platform

StruMind is a comprehensive, cloud-native structural engineering platform that combines the capabilities of ETABS, STAAD.Pro, and Tekla Structures into one unified AI-powered system.

## 🏗️ Features

### Core Capabilities
- **Structural Analysis**: Linear/non-linear static, dynamic, buckling, P-Delta analysis
- **Design Modules**: RC, steel, composite, foundation design per international codes
- **Detailing Engine**: Automated reinforcement and steel detailing with drawings
- **BIM Integration**: Full IFC 4.x support with 3D visualization
- **Cloud Computing**: Scalable backend with real-time collaboration

### Supported Design Codes
- **Concrete**: IS 456, ACI 318, Eurocode 2
- **Steel**: IS 800, AISC 360, Eurocode 3
- **Seismic**: IS 1893, ASCE 7, Eurocode 8
- **Wind**: IS 875, ASCE 7, Eurocode 1

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.12+ (for local development)
- PostgreSQL 15+ (for local development)
- Redis 7+ (for local development)

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/mrfamily9890/Strumind.git
   cd Strumind
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:12000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Celery Flower: http://localhost:5555

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database
createdb strumind
alembic upgrade head

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

#### Background Tasks
```bash
cd backend
celery -A tasks.celery_app worker --loglevel=info
```

## 📁 Project Structure

```
Strumind/
├── backend/                 # Python FastAPI backend
│   ├── core/               # Core modeling engine
│   ├── solver/             # Analysis solver engine
│   ├── design/             # Design modules
│   ├── detailing/          # Detailing engine
│   ├── bim/                # BIM export/import
│   ├── api/                # REST API endpoints
│   ├── db/                 # Database models & migrations
│   ├── auth/               # Authentication & authorization
│   └── tasks/              # Background tasks (Celery)
├── frontend/               # Next.js React frontend
│   └── src/
│       ├── components/     # React components
│       ├── pages/          # Next.js pages
│       ├── hooks/          # Custom React hooks
│       ├── stores/         # State management (Zustand)
│       └── services/       # API services
├── deployment/             # Docker, Kubernetes, Terraform
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## 🔧 Development Phases

### Phase 1: ✅ Backend + Frontend Scaffolding
- [x] Project structure setup
- [x] Docker configuration
- [x] Basic FastAPI backend
- [x] Next.js frontend with UI components
- [x] Database configuration

### Phase 2: 🚧 Database Schema Creation
- [ ] User & organization models
- [ ] Project & model entities
- [ ] Structural element models
- [ ] Analysis & design result models

### Phase 3: 📋 Core Modeling Module
- [ ] Node & coordinate system
- [ ] Structural elements (beams, columns, slabs, walls)
- [ ] Material & section libraries
- [ ] Load definition & combinations
- [ ] Boundary conditions

### Phase 4: 🔬 Solver Engine
- [ ] Global stiffness matrix generation
- [ ] Linear static analysis
- [ ] Non-linear analysis
- [ ] Dynamic analysis (modal, response spectrum)
- [ ] Buckling & P-Delta analysis

### Phase 5: 📐 Design Modules
- [ ] RC design (IS 456, ACI 318, EC2)
- [ ] Steel design (IS 800, AISC 360, EC3)
- [ ] Foundation design
- [ ] Connection design

### Phase 6: 📋 Detailing Module
- [ ] Reinforcement detailing
- [ ] Steel connection detailing
- [ ] Drawing generation
- [ ] Bar bending schedules

### Phase 7: 🏗️ BIM Export Module
- [ ] IFC 4.x export/import
- [ ] 3D model generation
- [ ] DXF export
- [ ] glTF export for web

### Phase 8: 🔌 API Exposure
- [ ] Complete REST API
- [ ] Authentication & authorization
- [ ] Multi-tenant support
- [ ] API documentation

### Phase 9: 💻 Frontend SaaS Platform
- [ ] User authentication
- [ ] Project management
- [ ] Model builder interface
- [ ] Analysis execution UI

### Phase 10: 🎨 3D Visualizer Module
- [ ] React Three Fiber integration
- [ ] Interactive 3D viewer
- [ ] Result visualization
- [ ] Section cutting

### Phase 11: ✏️ Model Editor Interface
- [ ] Drag & drop modeling
- [ ] Grid snapping
- [ ] Property assignment
- [ ] Load application UI

### Phase 12: 👥 User Management
- [ ] Multi-tenant architecture
- [ ] Role-based access control
- [ ] Organization management
- [ ] Collaboration features

### Phase 13: ☁️ Deployment & Scalability
- [ ] Kubernetes deployment
- [ ] Auto-scaling configuration
- [ ] Monitoring & logging
- [ ] Performance optimization

### Phase 14: 💰 Billing & Monetization
- [ ] Stripe integration
- [ ] Subscription management
- [ ] Usage tracking
- [ ] Billing dashboard

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Documentation: [docs.strumind.com](https://docs.strumind.com)
- Issues: [GitHub Issues](https://github.com/mrfamily9890/Strumind/issues)
- Discussions: [GitHub Discussions](https://github.com/mrfamily9890/Strumind/discussions)

## 🏢 Commercial Use

StruMind is designed as a commercial SaaS platform. For enterprise licensing and support, contact us at enterprise@strumind.com.

---

**StruMind** - Revolutionizing structural engineering with AI-powered cloud technology.