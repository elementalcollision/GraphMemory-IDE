# **Consolidated Enhancement PRD: GraphMemoryIDE**

## **1\. Introduction and Overall Assessment**

**Overall Assessment:** The GraphMemory-IDE project is well-structured with a commendable emphasis on security, particularly in its Docker configurations and deployment scripts. The existing documentation is thorough and serves as a strong foundation. This document outlines key areas for enhancement to improve stability, performance, security, and to integrate new capabilities like the Model Memory Protocol (MMP) v0.1.

## **2\. Goals**

* Enhance the stability and robustness of the application.  
* Improve performance, especially for resource-intensive operations.  
* Strengthen security across all components.  
* Prepare the codebase for future integrations and scalability.  
* Integrate foundational elements of the Model Memory Protocol (MMP) v0.1.  
* Improve developer experience and maintainability.

## **3\. Proposed Enhancements**

### **3.1. Server-Side Enhancements (FastAPI)**

* **Health Endpoint:**  
  * **Requirement:** Expose a /health endpoint.  
  * **Reasoning:** The CLI's health command expects this endpoint (currently cli/commands.mjs fetches http://localhost:8080/health). Implementing this will allow CLI health checks and container health probes to function correctly.  
* **Embedding Model Caching & Configuration:**  
  * **Requirement:** Load the SentenceTransformer model once during application startup and reuse it. Make the embedding model name (e.g., all-MiniLM-L6-v2) configurable.  
  * **Reasoning:** Currently, the Top-K search handler creates a new SentenceTransformer instance on each request, which is inefficient. Caching will reduce latency. Configurability allows flexibility.  
* **Telemetry Event Data Serialization:**  
  * **Requirement:** Use JSON serialization/deserialization (e.g., json.dumps/json.loads) for TelemetryEvent.data.  
  * **Reasoning:** Events are currently stored using str(event.data) and parsed with ast.literal\_eval. JSON is clearer, safer, and avoids potential parsing issues.  
* **API Pagination:**  
  * **Requirement:** Implement API pagination for list endpoints (e.g., telemetry queries).  
  * **Reasoning:** To improve performance and manageability when dealing with large datasets.  
* **Production User System:**  
  * **Requirement:** Replace the fake\_users\_db in auth.py with a robust solution for a production environment.  
  * **Reasoning:** The current fake\_users\_db is suitable only for development.

### **3.2. Database Enhancements (Kuzu)**

* **Graceful Database Connection Management:**  
  * **Requirement:** Transition Kuzu connection management from module-level globals to a per-request or connection pool model. Register FastAPI startup/shutdown events to manage the connection lifecycle (including loading the vector extension only once).  
  * **Reasoning:** The Kuzu connection is currently created at import time and never explicitly closed. Proper lifecycle management will improve robustness and resource utilization.  
* **TelemetryEvent Primary Key:**  
  * **Requirement:** Change the primary key for TelemetryEvent nodes from a timestamp to a UUID.  
  * **Reasoning:** To ensure absolute uniqueness of primary keys.  
* **Index and Projection Graph Creation:**  
  * **Requirement:** Move the creation of Kuzu indexes and projected graphs out of live API calls (e.g., /tools/topk) to an initialization, startup, or dedicated management process.  
  * **Reasoning:** Performing these operations during live API calls can lead to performance bottlenecks.  
* **OSF Data Integration Scaffolding:**  
  * **Requirement:** Provide a module or script for dataset ingestion, specifically to prepare for potential future use of the OSF dataset.  
  * **Reasoning:** The project goals mention this, and having scaffolding will ease future implementation.

### **3.3. Command-Line Interface (CLI) Enhancements**

* **Input Sanitization:**  
  * **Requirement:** Implement robust input sanitization for all CLI options that might be used in system commands or queries.  
  * **Reasoning:** To prevent potential security vulnerabilities like command injection.  
* **Update Lock Atomicity:**  
  * **Requirement:** Verify and, if necessary, harden the atomicity of the update lock mechanism (UpdateStateManager.acquireLock()).  
  * **Reasoning:** Critical for ensuring the integrity of the update process.  
* **Secure Update Plan Source:**  
  * **Requirement:** Ensure update plans are fetched from a secured, trusted source, replacing any hardcoded sample URLs.  
  * **Reasoning:** To prevent malicious updates.  
* **Error Reporting for Rollback:**  
  * **Requirement:** Improve the clarity and detail of error reporting if a rollback operation itself fails.  
  * **Reasoning:** To aid in diagnosing and resolving update issues.

### **3.4. Docker & Deployment Enhancements**

* **Service-Specific Seccomp Profiles:**  
  * **Requirement:** Tailor seccomp profiles on a per-service basis (e.g., mcp-server vs. kestra).  
  * **Reasoning:** For tighter security control by limiting system calls available to each service.  
* **Pin Kestra Docker Image Version:**  
  * **Requirement:** Pin the Kestra Docker image to a specific version instead of using latest.  
  * **Reasoning:** To ensure reproducible builds and avoid unexpected breaking changes from upstream.  
* **Review Container Capabilities:**  
  * **Requirement:** Evaluate and potentially remove unnecessary Linux capabilities (e.g., NET\_BIND\_SERVICE for mcp-server if it only uses non-privileged ports).  
  * **Reasoning:** Adherence to the principle of least privilege.  
* **Production Secrets Management:**  
  * **Requirement:** Enhance production secrets management (e.g., avoid logging a generated JWT secret).  
  * **Reasoning:** To prevent accidental exposure of sensitive information.

### **3.5. Testing and Quality Assurance**

* **Authentication Endpoint Tests:**  
  * **Requirement:** Add tests for the /auth/token endpoint in server/test\_main.py.  
  * **Reasoning:** server/test\_main.py currently covers telemetry and Top-K endpoints but lacks auth tests. This will protect against regressions in authentication logic.  
* **Expand Integration Test Coverage:**  
  * **Requirement:** Broaden integration test coverage, especially for new MMP features (see section 3.6) and critical failure scenarios (e.g., rollback failures).  
  * **Reasoning:** To ensure overall system stability and correctness.

### **3.6. Model Memory Protocol (MMP) v0.1 Integration Scaffolding**

This section outlines the foundational structures for MMP integration, not full implementation.

* **Core MMP Concepts:**  
  * **Episodic Memory Module (EMM):** For persistent identity narratives.  
  * **Procedural Memory Module (PMM):** For real-time interaction chronicles (existing TelemetryEvent system aligns well).  
  * Cryptographically-anchored privacy controls.  
  * Ethical behavior and auditability mechanisms.  
* **Database Schema Additions/Enhancements (Kuzu GraphDB):**  
  * **New Node Types:**  
    * IdentityNarrative: To store EMM elements (ID, content, source, importance, timestamps, tags).  
    * CorePrinciple: For AI's guiding principles (ID, statement, active status, category).  
    * MemoryAnchor: (Placeholder) For future cryptographic anchoring (ID, target node, hash, signature).  
  * **Enhancements to TelemetryEvent (for PMM):**  
    * Add an optional privacySensitivity field.  
    * Add a foreign key to IdentityNarrative (e.g., associatedNarrativeId).  
* **API Endpoint Additions/Modifications (FastAPI Server):**  
  * **EMM Endpoints:** Basic CRUD operations for /memory/narratives and /memory/principles.  
  * **PMM Endpoint Updates:** Modify /telemetry/ingest, /telemetry/query, /telemetry/list to support the new TelemetryEvent fields.  
  * **Privacy & Audit Placeholders:**  
    * Basic /memory/forget endpoint (for best-effort deletion initially).  
    * Basic /memory/audit/{nodeId} (for basic metadata retrieval).  
* **Conceptual Service Modules (Python):**  
  * MemoryLifecycleManager: Placeholder for managing memory retention and the forget functionality.  
  * PrivacyManager: Placeholder for future encryption and fine-grained access control logic.

### **3.7. Cross-Cutting Improvements**

* **Standardize Logging Practices:**  
  * **Requirement:** Review and standardize logging practices across all components (server, CLI).  
  * **Reasoning:** For consistent, effective monitoring and debugging.

## **4\. Documentation Updates**

* **Requirement:** Update all relevant documentation files (README.md, DOCUMENTATION.md, API\_GUIDE.md, DEVELOPER\_GUIDE.md, USER\_GUIDE.md, etc.) to reflect all changes implemented from this PRD.  
* **Key Areas for Updates:**  
  * New /health endpoint.  
  * Configuration for embedding model.  
  * Changes to TelemetryEvent structure and serialization.  
  * Database connection management strategy.  
  * New Kuzu node types and relationships for MMP.  
  * New API endpoints for MMP (narratives, principles, forget, audit).  
  * Updates to system architecture diagrams and data flow descriptions.  
  * CLI enhancements and security considerations.  
  * Docker and deployment security updates.

## **5\. Success Metrics**

* Successful implementation of a /health endpoint usable by CLI and container probes.  
* Measurable reduction in latency for Top-K search requests due to model caching.  
* Elimination of ast.literal\_eval for telemetry data.  
* Demonstrable graceful shutdown and startup of database connections.  
* CI tests passing for new authentication endpoint coverage.  
* Successful creation and querying of new MMP-related Kuzu nodes and relationships via new API endpoints.  
* Updated documentation accurately reflecting all changes.