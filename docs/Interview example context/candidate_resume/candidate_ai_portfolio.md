# Candidate AI Portfolio: Shaktisinh Sodha

## Portfolio Overview

**Investment**: 500+ hours over 12 months (2024-present)
**Repositories**: 3 comprehensive GitHub portfolios
**Focus**: Production-ready implementations, not just tutorials
**Approach**: Learn by building real systems, deployed to cloud

---

## Portfolio 1: Agentic AI Engineering

**Repository**: `Experiments_with_agenticAI`
**Focus**: Cutting-edge autonomous agents and multi-agent systems

### Key Projects & Capabilities

#### 1. Production Multi-Agent Systems (CrewAI)
**Implementation**:
- Architected autonomous "Engineering Teams" crew
  - Roles: Planner, Developer, Reviewer, Tester
  - Autonomous task decomposition and execution
  - Code generation, review, and iteration without human intervention

- Built "Financial Research" crew
  - Analyst agent: Market research and data gathering
  - Strategist agent: Investment thesis development
  - Writer agent: Report generation
  - Multi-step workflow with inter-agent communication

**Technical Details**:
- Role-based agent design with specialized tools
- Memory persistence across agent interactions
- Delegation patterns for complex task chains
- Error handling and retry logic

**Relevance to Smarsh**:
- Multi-agent compliance workflows (Level 1 analyst → Level 2 escalation)
- Autonomous alert triage (similar to Smarsh's GenAI roadmap)
- Collaborative AI systems for complex investigations

#### 2. Stateful Workflows (LangGraph)
**Implementation**:
- Human-in-the-Loop approval systems for sensitive operations
- State machines with conditional branching
- Checkpointing and rollback capabilities
- Graph-based execution with cycles and feedback loops

**Use Cases Built**:
- Multi-step research with human validation gates
- Document processing pipeline with quality checks
- Customer support automation with escalation paths

**Technical Details**:
- Graph state management
- Conditional edges based on agent outputs
- Persistence layer for long-running workflows
- Error recovery and state repair

**Relevance to Smarsh**:
- Enterprise-grade reliability requirements
- Human oversight for high-risk compliance decisions
- Audit trails and state inspection for regulatory purposes

#### 3. Model Context Protocol (MCP)
**Implementation**:
- Designed and deployed custom MCP servers
- Standardized tool interfaces for AI agents
- Protocol-based access to databases and APIs
- Secure, versioned tool definitions

**Systems Built**:
- Database MCP server: Secure SQL access for agents
- API wrapper MCP server: Rate-limited external API calls
- File system MCP server: Sandboxed file operations

**Technical Details**:
- JSON-RPC protocol implementation
- Authentication and authorization layers
- Resource management and throttling
- Comprehensive error handling

**Relevance to Smarsh**:
- Standardized agent-to-system interfaces
- Security and access control for AI systems
- Future-proof architecture for evolving AI capabilities

#### 4. Distributed Systems (AutoGen)
**Implementation**:
- Distributed coding agents with autonomous debugging
- Group chat collaboration between specialized agents
- Parallel task execution with result aggregation
- Consensus mechanisms for multi-agent decisions

**Relevance to Smarsh**:
- Distributed compliance processing across global regions
- Multi-model consensus for high-stakes decisions
- Scalability for processing millions of messages

---

## Portfolio 2: LLM Engineering & RAG

**Repository**: `Experiments_with_LLMs`
**Focus**: Foundational to advanced LLM techniques, production deployment

### Key Projects & Capabilities

#### 1. Autonomous Deal Hunter
**Description**: Multi-agent system deployed on Modal (Serverless) running 24/7

**Architecture**:
- Scraper agent: Autonomous web scraping across e-commerce sites
- Analyzer agent: Price trend analysis and prediction
- Alerter agent: Notification system for deal opportunities
- Scheduler: Serverless cron for continuous operation

**Technical Stack**:
- Modal for serverless Python
- BeautifulSoup/Playwright for scraping
- LangChain for agent orchestration
- OpenAI GPT-4 for analysis
- Upstash Redis for state persistence

**Production Metrics**:
- 100+ products monitored continuously
- <$5/month operational cost (serverless efficiency)
- 99% uptime over 6 months

**Relevance to Smarsh**:
- Serverless architecture for cost-effective AI workloads
- Always-on monitoring systems
- Scalable data processing

#### 2. Advanced RAG Pipelines
**Implementations**:
- **Semantic Search**: ChromaDB + OpenAI embeddings
- **Hybrid Search**: Keyword + vector search combination
- **Reranking**: Cohere reranker for precision improvement
- **Query Rewriting**: LLM-based query optimization for better retrieval

**Technical Techniques**:
- Chunking strategies (fixed-size, semantic, hierarchical)
- Metadata filtering for targeted retrieval
- Parent-child document relationships
- Multi-query generation for comprehensive coverage

**RAG Pipeline Components**:
1. Document ingestion and preprocessing
2. Embedding generation (text-embedding-004, OpenAI Ada)
3. Vector database indexing
4. Query processing and rewriting
5. Retrieval with top-k selection
6. Reranking for precision
7. Context assembly and prompt construction
8. LLM generation with citations

**Metrics Achieved**:
- 85% answer accuracy on custom dataset
- <500ms retrieval latency at 100K document scale
- 40% improvement with reranking vs. naive retrieval

**Relevance to Smarsh**:
- Smarsh Conduct module uses similar RAG architecture
- Document retrieval for eDiscovery
- Semantic search across petabytes of communications
- Citation and source tracking for compliance

#### 3. Model Fine-Tuning (QLoRA)
**Achievement**: Successfully fine-tuned Llama 3.1 8B on consumer hardware

**Technical Details**:
- 4-bit quantization for memory efficiency
- LoRA (Low-Rank Adaptation) for parameter-efficient tuning
- Consumer GPU (RTX 3090, 24GB VRAM)
- Training on custom pricing prediction dataset

**Results**:
- 2x better performance vs. base model on specialized task
- 95% memory reduction vs. full fine-tuning
- 6-hour training time for 10K examples

**Data Pipeline**:
- Custom dataset curation (5K examples)
- Data augmentation techniques
- Train/validation/test splits
- Evaluation framework (BLEU, ROUGE, perplexity)

**Relevance to Smarsh**:
- Custom model fine-tuning for compliance domain
- Efficiency techniques for cost reduction
- Specialized models for financial language understanding
- Internal model development capability

---

## Portfolio 3: AI in Production

**Repository**: `AI_in_Production`
**Focus**: End-to-end AI applications, deployment, scalability

### Key Projects & Capabilities

#### 1. Full-Stack SaaS Platform
**Description**: Scalable GenAI application with real-time streaming

**Tech Stack**:
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python), async/await patterns
- **AI**: OpenAI GPT-4 with streaming responses
- **Auth**: Clerk authentication
- **Hosting**: Vercel (frontend), Modal (backend)
- **Database**: PostgreSQL (Neon), Prisma ORM

**Features**:
- Real-time token streaming for responsive UX
- User authentication and session management
- Rate limiting and quota management
- Error handling and fallbacks
- Responsive design

**Production Deployment**:
- Deployed to production with custom domain
- CI/CD pipeline with GitHub Actions
- Monitoring with Sentry
- Analytics with PostHog

**Relevance to Smarsh**:
- Full-stack development capability
- Real-time streaming for interactive demos
- Production deployment experience
- Can build custom POC demos if needed

#### 2. Cyber Security Agent
**Description**: MCP agent with automated code vulnerability analysis

**Architecture**:
- MCP server for tool standardization
- Semgrep integration for static analysis
- Terraform for infrastructure provisioning
- Docker for containerization
- AWS deployment (Lambda + S3)

**Capabilities**:
- Automated security scanning of codebases
- Vulnerability prioritization and reporting
- Integration with CI/CD pipelines
- Compliance reporting (OWASP Top 10, CWE)

**Technical Highlights**:
- Infrastructure as Code (Terraform)
- Serverless architecture for cost efficiency
- MCP protocol for extensibility
- Structured output for programmatic consumption

**Relevance to Smarsh**:
- Security-first mindset
- Automated compliance checking
- Integration with existing workflows
- Infrastructure automation experience

#### 3. Digital Twin
**Description**: Stateful, personality-mimicking agent with long-term memory

**Technical Implementation**:
- **Memory System**: SQLite for persistent storage
- **Personality Model**: Fine-tuned on conversational data
- **State Management**: Conversation history, user preferences, context
- **Deployment**: Docker containerization, AWS App Runner
- **Scalability**: Stateless architecture with external state store

**Features**:
- Remembers past conversations across sessions
- Adapts responses based on user interaction history
- Personality consistency over time
- Privacy-respecting data handling

**Relevance to Smarsh**:
- Long-term memory systems (similar to Smarsh's persistent candidate profile)
- Stateful applications in production
- Data persistence strategies
- Privacy and data governance

---

## AI/ML Expertise Summary

### Demonstrated Capabilities

**1. Agentic Systems**:
- Multi-agent collaboration and orchestration
- Autonomous task decomposition and execution
- Human-in-the-loop workflows for enterprise safety

**2. LLM Engineering**:
- Fine-tuning and customization
- Prompt engineering and optimization
- Model selection and evaluation

**3. RAG Architectures**:
- End-to-end retrieval pipelines
- Semantic search and hybrid techniques
- Context assembly and prompt construction

**4. Production Deployment**:
- Serverless architectures (Modal, AWS Lambda)
- Full-stack applications (Next.js + FastAPI)
- CI/CD and monitoring

**5. Infrastructure**:
- Docker containerization
- Terraform IaC
- Cloud deployment (AWS, Vercel, Modal)

### Alignment with Smarsh's AI Roadmap

**Smarsh Capability** → **My Portfolio Proof**

**Intelligent Agent for Alert Triage** → Multi-agent systems with CrewAI, autonomous decision-making

**GenAI for Investigation Summaries** → RAG pipelines, document analysis, report generation

**Behavioral Profiling** → Anomaly detection implementations, pattern recognition

**Context-Aware Analysis** → RAG with hybrid search, metadata filtering, reranking

**Prompt Monitoring for GenAI Risk** → Security agent, policy enforcement, compliance checking

---

## Portfolio Impact on Interview

### Credibility in AI Discussions
Can speak peer-to-peer with Smarsh's AI/ML engineers about:
- Digital Reasoning NLP vs. modern LLMs
- RAG architecture trade-offs
- Multi-agent orchestration patterns
- Production deployment best practices

### Differentiation
Most SEs talk about AI features they sell. I can:
- Explain how the technology actually works
- Discuss implementation challenges and solutions
- Suggest architectural improvements
- Prototype new capabilities during POCs

### Demo Engineering
Can build custom demos for POCs:
- Mock AI alert triage interfaces
- RAG-based document search prototypes
- Multi-agent workflow visualizations
- Real-time streaming compliance interfaces

### Product Feedback Loop
Can provide valuable input to Product team:
- Technical feasibility of roadmap items
- Competitive AI feature gaps
- Customer-requested AI capabilities
- Implementation complexity estimates
